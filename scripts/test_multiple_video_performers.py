#!/usr/bin/env python3
"""Validate performer extraction against several YouTube descriptions; never writes videos.json."""
import json, os, re, urllib.parse, urllib.request
VIDEO_IDS = ["7coRRt9H-ZQ", "R5V5SBGQtCs", "3mYn8dfviPc"]

def extract(description):
    marker = "【出演者】"
    if marker not in description:
        return None
    section = description.split(marker, 1)[1]
    section = re.split(r"\n\s*【[^】]+】", section, maxsplit=1)[0]
    names = []
    for line in section.splitlines():
        if "→" not in line:
            continue
        name = line.split("→", 1)[0].strip()
        name = re.sub(r"^[\s・、]+|[\s・、]+$", "", name)
        if name and name not in names:
            names.append(name)
    return names

def main():
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        raise SystemExit("YOUTUBE_API_KEY is not set.")
    params = urllib.parse.urlencode({"part":"snippet", "id":",".join(VIDEO_IDS), "key":key})
    req = urllib.request.Request("https://www.googleapis.com/youtube/v3/videos?" + params, headers={"User-Agent":"OmocoroVideoDatabase/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    found = {item["id"]: item for item in payload.get("items", [])}
    problems = []
    print("VIDEOS_REQUESTED:", len(VIDEO_IDS))
    print("VIDEOS_RETURNED:", len(found))
    for video_id in VIDEO_IDS:
        item = found.get(video_id)
        print("\nVIDEO_ID:", video_id)
        if not item:
            print("STATUS: NOT_RETURNED_BY_API")
            problems.append(video_id)
            continue
        snippet = item.get("snippet") or {}
        description = snippet.get("description") or ""
        names = extract(description)
        print("TITLE:", snippet.get("title", ""))
        print("DESCRIPTION_RETRIEVED:", "yes" if description else "no_or_empty")
        if names is None:
            print("PERFORMER_SECTION: NOT_FOUND")
            print("PERFORMERS_JSON: null")
            problems.append(video_id)
        else:
            print("PERFORMER_SECTION: FOUND")
            print("PERFORMERS_COUNT:", len(names))
            print("PERFORMERS_JSON:", json.dumps(names, ensure_ascii=False))
            if not names:
                problems.append(video_id)
    print("\nTEST_RESULT:", "PASS" if not problems else "REVIEW_REQUIRED")
    if problems:
        print("VIDEOS_REQUIRING_REVIEW:", json.dumps(problems))

if __name__ == "__main__":
    main()
