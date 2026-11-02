#!/usr/bin/env python3
"""Update performers only from the 【出演者】 section of each YouTube description.

Missing or unparseable sections are left unchanged and reported for manual review.
No performer names are inferred from thumbnails, titles, archive tags, or old records.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path("data/videos.json")
API = "https://www.googleapis.com/youtube/v3/videos"
BATCH_SIZE = 50
MARKER = "【出演者】"


def extract_performers(description):
    """Return exact credited names, or None when the section is absent/ambiguous."""
    if not isinstance(description, str) or MARKER not in description:
        return None
    section = description.split(MARKER, 1)[1]
    # The credited section ends at the next Japanese bracketed heading.
    section = re.split(r"\n\s*【[^】]+】", section, maxsplit=1)[0]
    names = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line or "→" not in line:
            continue
        name = line.split("→", 1)[0].strip()
        name = re.sub(r"^[\s・●■◆-]+|[\s・●■◆-]+$", "", name)
        if not name:
            continue
        if name not in names:
            names.append(name)
    return names if names else None


def fetch_batch(video_ids, api_key):
    query = urllib.parse.urlencode({
        "part": "snippet",
        "id": ",".join(video_ids),
        "key": api_key,
    })
    request = urllib.request.Request(
        f"{API}?{query}",
        headers={"User-Agent": "OmocoroVideoDatabase/1.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return {item["id"]: item for item in payload.get("items", [])}


def main():
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY is not set.")
    if not DATA.exists():
        raise SystemExit(f"{DATA} does not exist.")

    videos = json.loads(DATA.read_text(encoding="utf-8"))
    if not isinstance(videos, list):
        raise SystemExit("data/videos.json must contain a JSON array.")

    by_id = {}
    for item in videos:
        if isinstance(item, dict):
            video_id = str(item.get("id") or item.get("videoId") or "")
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                by_id[video_id] = item

    ids = list(by_id)
    updated = 0
    missing_video = []
    missing_section = []
    empty_section = []
    batches = [ids[i:i + BATCH_SIZE] for i in range(0, len(ids), BATCH_SIZE)]

    for batch_number, batch in enumerate(batches, start=1):
        returned = fetch_batch(batch, api_key)
        print(f"BATCH {batch_number}/{len(batches)}: requested={len(batch)} returned={len(returned)}")
        for video_id in batch:
            item = returned.get(video_id)
            if item is None:
                missing_video.append(video_id)
                continue

            snippet = item.get("snippet") or {}
            description = snippet.get("description") or ""
            performers = extract_performers(description)
            if performers is None:
                if MARKER in description:
                    empty_section.append(video_id)
                else:
                    missing_section.append(video_id)
                continue

            # Replace old values only when the YouTube description has a valid,
            # non-empty credited list. Keep the exact order and spelling.
            by_id[video_id]["performers"] = performers
            by_id[video_id]["performerSource"] = "YouTube概要欄【出演者】"
            by_id[video_id]["reviewStatus"] = "出演者：YouTube概要欄から取得"
            updated += 1

    DATA.write_text(json.dumps(videos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("VIDEOS_INDEXED:", len(ids))
    print("PERFORMERS_UPDATED:", updated)
    print("VIDEO_NOT_RETURNED:", len(missing_video))
    print("DESCRIPTION_WITHOUT_SECTION:", len(missing_section))
    print("SECTION_WITHOUT_PARSEABLE_NAMES:", len(empty_section))
    if missing_video:
        print("VIDEO_NOT_RETURNED_IDS:", json.dumps(missing_video, ensure_ascii=False))
    if missing_section:
        print("DESCRIPTION_WITHOUT_SECTION_IDS:", json.dumps(missing_section, ensure_ascii=False))
    if empty_section:
        print("SECTION_WITHOUT_NAMES_IDS:", json.dumps(empty_section, ensure_ascii=False))


if __name__ == "__main__":
    main()
