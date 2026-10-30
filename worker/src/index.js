const REPO = 'NORTH5972/omocorochannel-database';
const BRANCH = 'main';
const DATA_PATH = 'data/videos.json';
const COOKIE = 'omoco_admin_session';
const SESSION_TTL = 8 * 60 * 60;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (url.pathname === '/login' && request.method === 'GET') return login(request, env);
      if (url.pathname === '/auth/callback' && request.method === 'GET') return callback(request, env);
      if (url.pathname === '/logout' && request.method === 'POST') return logout(request, env);
      if (url.pathname.startsWith('/api/')) {
        const session = await getSession(request, env);
        if (!session) return json({ error: 'ログインしてください。' }, 401);
        if (session.login.toLowerCase() !== 'NORTH5972'.toLowerCase()) return json({ error: '編集権限がありません。' }, 403);
        if (url.pathname === '/api/me' && request.method === 'GET') return json({ login: session.login });
        if (url.pathname === '/api/videos' && request.method === 'GET') return getVideos(env);
        if (url.pathname === '/api/save' && request.method === 'POST') {
          if (request.headers.get('Origin') !== url.origin) return json({ error: '不正なリクエストです。' }, 403);
          return saveVideos(request, env);
        }
        return json({ error: '見つからないAPIです。' }, 404);
      }
      return env.ASSETS.fetch(request);
    } catch (error) {
      console.error(error);
      return json({ error: 'サーバー側でエラーが発生しました。設定とログを確認してください。' }, 500);
    }
  }
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
}
function cookieValue(request, name) {
  const header = request.headers.get('Cookie') || '';
  const item = header.split(';').map(x => x.trim()).find(x => x.startsWith(name + '='));
  return item ? item.slice(name.length + 1) : '';
}
function cookieHeader(value, maxAge) {
  return COOKIE + '=' + value + '; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=' + maxAge;
}
async function login(request, env) {
  const state = randomToken();
  await env.SESSIONS.put('state:' + state, '1', { expirationTtl: 600 });
  const callbackUrl = new URL('/auth/callback', request.url).toString();
  const target = new URL('https://github.com/login/oauth/authorize');
  target.searchParams.set('client_id', 'Iv23liBRWSqaFKy57lHA');
  target.searchParams.set('redirect_uri', callbackUrl);
  target.searchParams.set('scope', 'read:user');
  target.searchParams.set('state', state);
  return Response.redirect(target.toString(), 302);
}
async function callback(request, env) {
  const url = new URL(request.url);
  const state = url.searchParams.get('state') || '';
  if (!state || !(await env.SESSIONS.get('state:' + state))) return new Response('認証状態を確認できませんでした。ログインし直してください。', { status: 400 });
  await env.SESSIONS.delete('state:' + state);
  const code = url.searchParams.get('code');
  if (!code) return new Response('GitHubから認証コードが返されませんでした。', { status: 400 });
  const tokenResponse = await fetch('https://github.com/login/oauth/access_token', {
    method: 'POST',
    headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: 'Iv23liBRWSqaFKy57lHA', client_secret: env.GITHUB_CLIENT_SECRET, code })
  });
  const tokenData = await tokenResponse.json();
  if (!tokenResponse.ok || !tokenData.access_token) return new Response('GitHub認証に失敗しました。', { status: 401 });
  const userResponse = await fetch('https://api.github.com/user', { headers: { 'Authorization': 'Bearer ' + tokenData.access_token, 'Accept': 'application/vnd.github+json', 'User-Agent': 'omocoro-video-admin' } });
  const user = await userResponse.json();
  if (!userResponse.ok || !user.login) return new Response('GitHubアカウントを確認できませんでした。', { status: 401 });
  if (String(user.login).toLowerCase() !== String('NORTH5972').toLowerCase()) {
    return new Response('このGitHubアカウントには編集権限がありません。', { status: 403, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }
  const sid = randomToken();
  await env.SESSIONS.put('session:' + sid, JSON.stringify({ login: user.login }), { expirationTtl: SESSION_TTL });
  return new Response('', { status: 302, headers: { 'Location': '/', 'Set-Cookie': cookieHeader(sid, SESSION_TTL), 'Cache-Control': 'no-store' } });
}
async function getSession(request, env) {
  const sid = cookieValue(request, COOKIE);
  if (!sid) return null;
  const raw = await env.SESSIONS.get('session:' + sid);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}
async function logout(request, env) {
  const sid = cookieValue(request, COOKIE);
  if (sid) await env.SESSIONS.delete('session:' + sid);
  return new Response(JSON.stringify({ ok: true }), { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'Set-Cookie': cookieHeader('', 0) } });
}
function randomToken() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
}

function derLength(length) {
  if (length < 128) return Uint8Array.of(length);
  const bytes = [];
  while (length > 0) { bytes.unshift(length & 255); length >>>= 8; }
  return Uint8Array.of(0x80 | bytes.length, ...bytes);
}
function derElement(tag, content) {
  const len = derLength(content.length);
  const out = new Uint8Array(1 + len.length + content.length);
  out[0] = tag; out.set(len, 1); out.set(content, 1 + len.length);
  return out;
}
function wrapPkcs1AsPkcs8(pkcs1) {
  const version = Uint8Array.of(0x02, 0x01, 0x00);
  const algorithm = Uint8Array.of(0x30, 0x0d, 0x06, 0x09, 0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x01, 0x01, 0x01, 0x05, 0x00);
  const octet = derElement(0x04, pkcs1);
  const content = new Uint8Array(version.length + algorithm.length + octet.length);
  content.set(version, 0); content.set(algorithm, version.length); content.set(octet, version.length + algorithm.length);
  return derElement(0x30, content);
}

async function githubAppToken(env) {
  const now = Math.floor(Date.now() / 1000);
  const enc = value => btoa(unescape(encodeURIComponent(value))).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  const header = enc(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const payload = enc(JSON.stringify({ iat: now - 30, exp: now + 540, iss: env.GITHUB_APP_ID }));
  const message = header + '.' + payload;
  const keyText = env.GITHUB_APP_PRIVATE_KEY.trim();
  const pem = keyText.replace(/-----BEGIN [^-]+-----|-----END [^-]+-----|\s/g, '');
  const binary = atob(pem);
  const der = Uint8Array.from(binary, c => c.charCodeAt(0));
  // GitHub App private keys are commonly PKCS#1; WebCrypto expects PKCS#8.
  const pkcs8 = keyText.includes('BEGIN RSA PRIVATE KEY') ? wrapPkcs1AsPkcs8(der) : der;
  const key = await crypto.subtle.importKey('pkcs8', pkcs8, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
  const signature = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', key, new TextEncoder().encode(message));
  const sig = btoa(String.fromCharCode.apply(null, Array.from(new Uint8Array(signature)))).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  const jwt = message + '.' + sig;
  const response = await fetch('https://api.github.com/app/installations/' + encodeURIComponent(env.GITHUB_INSTALLATION_ID) + '/access_tokens', {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + jwt, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'omocoro-video-admin', 'Content-Type': 'application/json' },
    body: JSON.stringify({ repositories: ['omocorochannel-database'], permissions: { contents: 'write' } })
  });
  const data = await response.json();
  if (!response.ok || !data.token) throw new Error('GitHub Appのインストールトークンを取得できませんでした: ' + JSON.stringify(data));
  return data.token;
}
async function getVideos(env) {
  const token = await githubAppToken(env);
  const response = await fetch('https://api.github.com/repos/' + REPO + '/contents/' + DATA_PATH + '?ref=' + BRANCH, {
    headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'omocoro-video-admin' }
  });
  const data = await response.json();
  if (!response.ok || !data.content) return json({ error: '動画データをGitHubから取得できませんでした。' }, 502);
  const bytes = Uint8Array.from(atob(data.content.replace(/\n/g, '')), c => c.charCodeAt(0));
  const videos = JSON.parse(new TextDecoder().decode(bytes));
  return json({ videos: videos.map(v => ({ id: v.id, title: v.title, publishedAt: v.publishedAt || '', performers: Array.isArray(v.performers) ? v.performers : [] })) });
}
function validDate(value) { const date = new Date(value + 'T00:00:00Z'); return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value; }
async function saveVideos(request, env) {
  let body;
  try { body = await request.json(); } catch { return json({ error: '送信データがJSONではありません。' }, 400); }
  if (!Array.isArray(body.updates) || body.updates.length < 1 || body.updates.length > 100) return json({ error: '一度に保存できる変更は1〜100件です。' }, 400);
  const seen = new Set();
  for (const u of body.updates) {
    if (!u || typeof u.id !== 'string' || seen.has(u.id)) return json({ error: '動画IDが不正または重複しています。' }, 400);
    seen.add(u.id);
    if (typeof u.publishedAt !== 'string' || (u.publishedAt !== '' && (!/^\d{4}-\d{2}-\d{2}$/.test(u.publishedAt) || !validDate(u.publishedAt)))) return json({ error: '公開日は実在する日付のYYYY-MM-DD形式か空欄にしてください。' }, 400);
    if (!Array.isArray(u.performers) || u.performers.length > 20 || u.performers.some(p => typeof p !== 'string' || p.length > 80)) return json({ error: '出演者の入力形式が不正です。' }, 400);
  }
  const token = await githubAppToken(env);
  const apiUrl = 'https://api.github.com/repos/' + REPO + '/contents/' + DATA_PATH;
  const get = await fetch(apiUrl + '?ref=' + BRANCH, { headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'omocoro-video-admin' } });
  const current = await get.json();
  if (!get.ok || !current.content || !current.sha) return json({ error: '現在の動画データを取得できません。' }, 502);
  const bytes = Uint8Array.from(atob(current.content.replace(/\n/g, '')), c => c.charCodeAt(0));
  const videos = JSON.parse(new TextDecoder().decode(bytes));
  const byId = new Map(videos.map(v => [v.id, v]));
  for (const u of body.updates) {
    const v = byId.get(u.id);
    if (!v) return json({ error: '対象の動画がデータ内にありません: ' + u.id }, 400);
    v.publishedAt = u.publishedAt;
    v.performers = [...new Set(u.performers.map(p => p.trim()).filter(Boolean))];
  }
  const content = JSON.stringify(videos, null, 2) + '\n';
  const encodedBytes = new TextEncoder().encode(content);
  let binary = '';
  for (let i = 0; i < encodedBytes.length; i += 0x8000) binary += String.fromCharCode.apply(null, encodedBytes.subarray(i, i + 0x8000));
  const put = await fetch(apiUrl, {
    method: 'PUT',
    headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'omocoro-video-admin', 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'Edit video metadata from admin interface', content: btoa(binary), sha: current.sha, branch: BRANCH })
  });
  const result = await put.json();
  if (!put.ok) {
    console.error('GitHub content update failed', result);
    return json({ error: 'GitHubへの保存に失敗しました。競合やGitHub Appの権限を確認してください。' }, 502);
  }
  return json({ ok: true, updated: body.updates.length, commit: result.commit && result.commit.html_url ? result.commit.html_url : '' });
}
