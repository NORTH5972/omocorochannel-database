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
