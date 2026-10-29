#!/usr/bin/env python3
"""Build a cumulative video index from the official YouTube channel.

Uses yt-dlp's flat channel listing to discover the archive without an API key,
then supplements it with YouTube's public RSS feed. It records metadata and links;
performer/protagonist/genre/end-screen labels are intentionally not guessed.
"""
import json
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CHANNEL_URL = "https://www.youtube.com/@omocorochannel/videos"
CHANNEL_ID = "UCOx-oLP9tOhiYwSK_m-yVxA"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
OUTPUT = Path("data/videos.json")
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/schemas/2015", "media": "http://search.yahoo.com/mrss/"}


def load_existing():
    if not OUTPUT.exists():
        return []
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("data/videos.json must contain a JSON array")
    return data


def normalize(video_id, title="", published="", url="", thumbnail="", description=""):
    return {
        "id": str(video_id),
        "title": title or "タイトル未取得",
        "publishedAt": published[:10] if published else "",
        "url": url if url.startswith("http") else f"https://www.youtube.com/watch?v={video_id}",
        "thumbnailUrl": thumbnail or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "performers": [],
        "protagonists": [],
        "genres": [],
        "endingScreen": "",
        "description": description or "",
        "source": "YouTubeチャンネル動画一覧",
        "reviewStatus": "タグ未確認",
    }


def get_full_channel_listing():
    command = [
        "yt-dlp", "--flat-playlist", "--dump-single-json",
        "--ignore-errors", "--no-warnings", "--skip-download",
        "--extractor-args", "youtube:lang=ja", CHANNEL_URL,
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=900)
    channel = json.loads(result.stdout)
    entries = channel.get("entries") or []
    found = {}
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        video_id = str(entry["id"])
        upload_date = entry.get("upload_date") or ""
        thumbnails = entry.get("thumbnails") or []
        thumbnail = entry.get("thumbnail") or (thumbnails[-1].get("url") if thumbnails else "")
        url = entry.get("webpage_url") or entry.get("original_url") or entry.get("url") or ""
        found[video_id] = normalize(
            video_id, entry.get("title") or "", upload_date, url, thumbnail,
            entry.get("description") or "",
        )
    return found, len(entries)


def get_rss_listing():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0 (compatible; OmocoroVideoIndex/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as response:
        root = ET.fromstring(response.read())
    found = {}
    for entry in root.findall("atom:entry", NS):
        video_id = entry.findtext("yt:videoId", default="", namespaces=NS)
        if not video_id:
            continue
        title = entry.findtext("atom:title", default="", namespaces=NS).strip()
        published = entry.findtext("atom:published", default="", namespaces=NS)
        link_el = entry.find("atom:link[@rel='alternate']", NS)
        url = link_el.get("href") if link_el is not None else ""
        thumb_el = entry.find("media:group/media:thumbnail", NS)
        thumbnail = thumb_el.get("url") if thumb_el is not None else ""
        found[video_id] = normalize(video_id, title, published, url, thumbnail)
    return found



def get_official_archive_dates():
    """Recover dates from Omocoro's official video archive, matching YouTube IDs."""
    import re
    from html.parser import HTMLParser
    from urllib.parse import urljoin

    base = "https://omocoro.jp/video/"
    seen_pages = set()
    found = {}
    found_titles = []
    queue = [base]

    class ArchiveParser(HTMLParser):
        """Collect visible archive text and links without assuming card markup."""
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.text_parts = []

        def handle_data(self, data):
            if data.strip():
                self.text_parts.append(data.strip())

        @property
        def text(self):
            return " ".join(self.text_parts)


    # The archive is paginated; cap the crawl to avoid an unbounded request loop.
    while queue and len(seen_pages) < 80:
        page = queue.pop(0)
        if page in seen_pages:
            continue
        seen_pages.add(page)
        try:
            req = urllib.request.Request(
                page, headers={"User-Agent": "Mozilla/5.0 (compatible; OmocoroVideoIndex/1.0)"}
            )
            with urllib.request.urlopen(req, timeout=25) as response:
                html = response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            print(f"Official archive page unavailable ({page}): {type(exc).__name__}")
            continue

        parser = ArchiveParser()
        parser.feed(html)
        page_text = " ".join(parser.text.split())
        # The archive cards are not consistently wrapped in <article> tags.
        # Record each visible date with the full page text and its position so
        # missing video titles can be matched to nearby dates.
        dates = list(re.finditer(r"([12]\d{3})[.]([01]\d)[.]([0-3]\d)", page_text))
        for match in dates:
            year, month, day = match.groups()
            found_titles.append((page_text, f"{year}-{month}-{day}", match.start()))

        # Keep direct ID matching as a fallback if the archive embeds YouTube links.
        ids = set(re.findall(
            r"(?:youtube(?:-nocookie)?\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})",
            html
        ))
        iso_dates = re.findall(r"(?:datetime|content|data-date)[\\"'=:\s]+([12]\d{3})[-./]([01]\d)[-./]([0-3]\d)", html)
        if iso_dates:
            year, month, day = iso_dates[0]
            for video_id in ids:
                found[video_id] = f"{year}-{month}-{day}"

        # Find rel=next regardless of whether href appears before or after rel.
        next_tag = re.search(r"<(?:a|link)\b(?=[^>]*\brel=['\"]next['\"])([^>]*)>", html, re.I)
        next_links = re.findall(r"\bhref=['\"]([^'\"]+)['\"]", next_tag.group(1), re.I) if next_tag else []
        if next_links:
            next_page = urljoin(page, next_links[0])
            if next_page not in seen_pages:
                queue.append(next_page)

    print(f"Official Omocoro archive: checked {len(seen_pages)} pages; matched {len(found)} YouTube IDs")
    return found, found_titles


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    existing = load_existing()
    by_id = {
        str(v.get("id") or v.get("videoId")): v
        for v in existing
        if isinstance(v, dict) and (v.get("id") or v.get("videoId"))
    }
    discovered = {}
    try:
        discovered, count = get_full_channel_listing()
        print(f"Channel archive listing entries: {count}; unique IDs: {len(discovered)}")
    except Exception as exc:
        print(f"WARNING: full archive crawl failed; continuing with RSS only: {type(exc).__name__}: {exc}")
    try:
        rss = get_rss_listing()
        print(f"RSS entries: {len(rss)}")
        discovered.update(rss)
    except Exception as exc:
        print(f"WARNING: RSS fetch failed: {type(exc).__name__}: {exc}")

    # Retry missing publication dates one video at a time. A single batch can fail
    # completely if one unavailable/private video causes yt-dlp to stop early.
    missing_ids = [
        str(v.get("id") or v.get("videoId"))
        for v in existing
        if isinstance(v, dict) and (v.get("id") or v.get("videoId"))
        and not str(v.get("publishedAt") or "").strip()
    ]
    recovered = 0
    failed = 0
    for video_id in missing_ids:
        command = [
            "yt-dlp", "--skip-download", "--dump-single-json", "--ignore-errors",
            "--no-warnings", "--no-playlist", f"https://www.youtube.com/watch?v={video_id}",
        ]
        try:
            result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=45)
            entry = None
            for line in result.stdout.splitlines():
                try:
                    candidate = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(candidate.get("id") or "") == video_id:
                    entry = candidate
                    break
            upload_date = (entry or {}).get("upload_date") or ""
            if len(upload_date) == 8 and upload_date.isdigit():
                discovered.setdefault(video_id, {})["publishedAt"] = (
                    f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                )
                recovered += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    print(f"Detailed metadata retry: recovered dates for {recovered}/{len(missing_ids)} previously undated videos; unresolved: {failed}")


    # The official Omocoro archive may retain publication dates even when YouTube
    # no longer exposes them through yt-dlp. Only accept dates tied to a matching ID.
    try:
        official_dates, official_title_dates = get_official_archive_dates()
        official_recovered = 0
        for video_id, published in official_dates.items():
            old = by_id.get(video_id)
            if old is not None and not str(old.get("publishedAt") or "").strip():
                old["publishedAt"] = published
                old["source"] = "オモコロ公式動画アーカイブ"
                official_recovered += 1

        # Some archive cards link to Omocoro articles rather than embedding YouTube.
        # In that case, match the exact existing video title against visible card text.
        import re
        def title_key(value):
            return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠ー]", "", str(value or "").lower())
        for old in by_id.values():
            if str(old.get("publishedAt") or "").strip():
                continue
            key = title_key(old.get("title"))
            if len(key) < 8:
                continue
            for archive_text, published, date_pos in official_title_dates:
                if key not in title_key(archive_text):
                    continue
                title_pos = archive_text.find(str(old.get("title") or ""))
                if title_pos < 0 or abs(title_pos - date_pos) > 500:
                    continue
                old["publishedAt"] = published
                old["source"] = "オモコロ公式動画アーカイブ（タイトル照合）"
                official_recovered += 1
                break
        print(f"Official archive date recovery: {official_recovered} previously undated videos")
    except Exception as exc:
        print(f"WARNING: official archive date recovery failed: {type(exc).__name__}: {exc}")

    added = 0
    for video_id, metadata in discovered.items():
        old = by_id.get(video_id)
        if old is None:
            by_id[video_id] = metadata
            added += 1
            continue
        for key in ("title", "publishedAt", "url", "thumbnailUrl", "description", "source"):
            if metadata.get(key):
                old[key] = metadata[key]
        old.setdefault("performers", [])
        old.setdefault("protagonists", [])
        old.setdefault("genres", [])
        old.setdefault("endingScreen", "")
        old.setdefault("reviewStatus", "タグ未確認")

    videos = sorted(by_id.values(), key=lambda v: (str(v.get("publishedAt", "")), str(v.get("id", ""))), reverse=True)
    OUTPUT.write_text(json.dumps(videos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"New videos added: {added}; total indexed: {len(videos)}")


if __name__ == "__main__":
    main()
