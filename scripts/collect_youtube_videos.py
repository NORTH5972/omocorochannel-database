#!/usr/bin/env python3
"""Import recent public video metadata from the official YouTube channel RSS feed.

YouTube's channel feed is limited to recent uploads. Existing hand-curated tags are
preserved; this script does not infer performers, protagonists, genres, or end screens.
"""
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CHANNEL_ID = "UCOx-oLP9tOhiYwSK_m-yVxA"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
OUTPUT = Path("data/videos.json")
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0 (compatible; OmocoroVideoIndex/1.0)"})
with urllib.request.urlopen(req, timeout=30) as response:
    xml_data = response.read()

root = ET.fromstring(xml_data)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
if OUTPUT.exists():
    existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
else:
    existing = []
if not isinstance(existing, list):
    raise ValueError("data/videos.json must contain a JSON array")

by_id = {str(v.get("id")): v for v in existing if isinstance(v, dict) and v.get("id")}
new_count = 0
for entry in root.findall("atom:entry", NS):
    video_id = entry.findtext("yt:videoId", default="", namespaces=NS)
    if not video_id:
        continue
    title = entry.findtext("atom:title", default="", namespaces=NS).strip()
    published = entry.findtext("atom:published", default="", namespaces=NS)
    link_el = entry.find("atom:link[@rel='alternate']", NS)
    url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"
    thumb_el = entry.find("media:group/media:thumbnail", NS)
    thumbnail = thumb_el.get("url") if thumb_el is not None else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    video = by_id.get(video_id)
    if video is None:
        video = {
            "id": video_id,
            "title": title,
            "publishedAt": published[:10] if published else "",
            "url": url,
            "thumbnailUrl": thumbnail,
            "performers": [],
            "protagonists": [],
            "genres": [],
            "endingScreen": "",
            "description": "",
            "source": "YouTube公式チャンネルRSS",
            "reviewStatus": "タグ未確認",
        }
        by_id[video_id] = video
        new_count += 1
    else:
        # Refresh only factual metadata; preserve any human-added tags/annotations.
        video["title"] = title or video.get("title", "")
        video["publishedAt"] = published[:10] if published else video.get("publishedAt", "")
        video["url"] = url or video.get("url", "")
        video["thumbnailUrl"] = thumbnail or video.get("thumbnailUrl", "")

# Keep newest entries first; entries collected in earlier runs remain in the database.
videos = sorted(by_id.values(), key=lambda v: (v.get("publishedAt", ""), v.get("id", "")), reverse=True)
OUTPUT.write_text(json.dumps(videos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"RSS entries: {len(root.findall('atom:entry', NS))}; new videos: {new_count}; total indexed: {len(videos)}")
