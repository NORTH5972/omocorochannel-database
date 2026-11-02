#!/usr/bin/env python3
"""Fetch one YouTube description and test extraction of the credited performers."""
import json
import os
import re
import urllib.parse
import urllib.request

API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
VIDEO_ID = "7coRRt9H-ZQ"
API_URL = "https://www.googleapis.com/youtube/v3/videos"


def main():
    if not API_KEY:
        raise SystemExit("YOUTUBE_API_KEY is not set.")

    query = urllib.parse.urlencode({
        "part": "snippet",
        "id": VIDEO_ID,
        "key": API_KEY,
    })
    request = urllib.request.Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": "OmocoroVideoDatabase/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    items = payload.get("items") or []
    if not items:
        raise SystemExit(f"YouTube API returned no video for {VIDEO_ID}")

    description = (items[0].get("snippet") or {}).get("description") or ""
    if "【出演者】" not in description:
        raise SystemExit("Description was retrieved, but 【出演者】 was not found.")

    section = description.split("【出演者】", 1)[1]
    # Each credited person is written as: name -> social account link.
    # Stop at the next bracketed heading, if present.
    section = re.split(r"\n\s*【[^】]+】", section, maxsplit=1)[0]
    performers = []
    for line in section.splitlines():
        if "→" not in line:
            continue
        name = line.split("→", 1)[0].strip()
        name = re.sub(r"^[\s・、]+|[\s・、]+$", "", name)
        if name and name not in performers:
            performers.append(name)

    print("VIDEO_ID:", VIDEO_ID)
    print("TITLE:", (items[0].get("snippet") or {}).get("title", ""))
    print("DESCRIPTION_RETRIEVED: yes")
    print("PERFORMERS_COUNT:", len(performers))
    print("PERFORMERS_JSON:", json.dumps(performers, ensure_ascii=False))
    expected = ["永田", "原宿", "ダ･ヴィンチ･恐山", "ARuFa", "加藤"]
    if performers != expected:
        raise SystemExit(
            "Extraction did not match the manually verified five names. "
            "Review the output before applying this parser to other videos."
        )
    print("TEST_RESULT: PASS")


if __name__ == "__main__":
    main()
