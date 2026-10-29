# 管理画面（Cloudflare Worker）

このWorkerは、GitHub Appによるリポジトリ限定の書き込み権限と、GitHub OAuthログインを使って動画メタデータを安全に編集するための管理画面です。公開サイトとは別の `workers.dev` URLで動作します。

## 重要な前提

- GitHub Pages側に書き込み用トークンを置かないでください。
- GitHub Appは `NORTH5972/omocorochannel-database` **だけ**にインストールしてください。
- 編集を許可するGitHubログイン名は `ADMIN_GITHUB_LOGIN` で指定します（初期想定値は `NORTH5972`）。
- この管理画面は現時点では公開日と出演者のみを編集します。タイトルや動画IDなどの基本情報は変更しません。
- 一度に保存できる変更は最大100件です。編集画面は30件ずつ表示します。
- 保存時に `data/videos.json` 全体を更新するため、保存直前に最新データをGitHubから読み込みます。自動収集処理と同時に保存した場合は、GitHub側で競合エラーになる可能性があります。

## 1. GitHub Appを作成する

GitHubの Settings → Developer settings → GitHub Apps → New GitHub App から作成します。

- GitHub App name：任意（例 `omocoro-video-admin`）
- Homepage URL：公開サイト `https://north5972.github.io/omocorochannel-database/`
- Callback URL：後で作るWorkerの `https://<WORKER名>.<ACCOUNT名>.workers.dev/auth/callback`
- Webhook：Activeをオフ
- Repository permissions：Contents = Read and write。他は原則No access
- Where can this GitHub App be installed? Only on this account
- Create後、Client IDとApp IDを控え、Client secretsでClient secretを作成
- Private keysで秘密鍵を生成・ダウンロード
- Install Appから、このリポジトリ `NORTH5972/omocorochannel-database` だけを選んでインストール
- インストール先URLの `/installations/<数字>` にある数字がInstallation ID

App作成画面で設定できる項目名はGitHub UIの更新で多少異なる場合があります。OAuth callback URLはWorker URLが確定してから設定し直してください。

## 2. Cloudflare WorkerとKVを作成する

Cloudflareアカウントを作成し、Workers & PagesでWorkerを作成します。CLIを使う場合はNode.js環境でWranglerを利用します。

1. CloudflareでKV namespaceを作成し、そのIDを `wrangler.toml` の `REPLACE_WITH_KV_NAMESPACE_ID` に入れます。
2. `wrangler.toml` の `name` を希望のWorker名に変更します。
3. Workerをデプロイします。
4. GitHub AppのCallback URLを、実際のWorker URLの `/auth/callback` に設定します。

CLIの例：

```sh
cd worker
npm install --save-dev wrangler
npx wrangler kv namespace create SESSIONS
# 出力されたnamespace IDをwrangler.tomlに記入
npx wrangler deploy
```

このリポジトリにはNode.jsの依存関係を追加していないため、上記コマンドはCloudflare Workerをデプロイする作業環境で実行してください。

## 3. Workerの環境変数とSecretを設定する

Workerの Settings → Variables and Secrets で次を設定します。

通常の変数：
- `GITHUB_APP_ID`：GitHub App ID
- `GITHUB_CLIENT_ID`：GitHub App Client ID
- `GITHUB_INSTALLATION_ID`：Installation ID
- `ADMIN_GITHUB_LOGIN`：編集を許可するGitHubログイン名（例 `NORTH5972`）

Secret：
- `GITHUB_CLIENT_SECRET`：GitHub AppのClient secret
- `GITHUB_APP_PRIVATE_KEY`：秘密鍵PEM全文（BEGIN/END行を含む）

秘密鍵・Client secretは、ソースコード、GitHub Pages、公開リポジトリのファイルに書かないでください。WorkerのSecretとしてのみ保存してください。

## 4. 動作確認

1. Worker URLを開き、「GitHubでログイン」を押します。
2. `ADMIN_GITHUB_LOGIN` に設定したアカウントで認証します。
3. 動画タイトルまたはIDで検索し、公開日・出演者を編集します。
4. 「変更を保存」を押し、GitHubにコミットが作成されることを確認します。
5. GitHub Pagesに反映されるまで少し待ち、公開サイトで確認します。

ログインできない場合はCallback URLとClient IDを確認します。保存できない場合は、GitHub Appが正しいリポジトリにインストールされ、ContentsのRead and write権限を持つかを確認してください。
