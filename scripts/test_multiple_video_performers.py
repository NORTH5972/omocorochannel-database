#!/usr/bin/env python3
"""Live regression test: known videos must match manually verified description credits."""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

spec_path = Path(__file__).with_name("collect_youtube_performers.py")
namespace = {}
exec(compile(spec_path.read_text(encoding="utf-8"), str(spec_path), "exec"), namespace)
extract_performers = namespace["extract_performers"]

EXPECTED = {
    "7coRRt9H-ZQ": ["永田", "原宿", "ダ･ヴィンチ･恐山", "ARuFa", "加藤"],
    "R5V5SBGQtCs": ["永田", "原宿", "ダ･ヴィンチ･恐山", "ARuFa", "加藤", "ヤスミノ", "かんち"],
    "3mYn8dfviPc": ["永田", "原宿", "ダ･ヴィンチ･恐山", "ARuFa", "加藤"],
}


def main():
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        raise SystemExit("YOUTUBE_API_KEY is not set.")
    ids = list(EXPECTED)
    query = urllib.parse.urlencode({"part": "snippet", "id": ",".join(ids), "key": key})
    request = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/videos?" + query,
        headers={"User-Agent": "OmocoroVideoDatabase/1.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    returned = {item["id"]: item for item in payload.get("items", [])}
    failures = []
    print("VIDEOS_REQUESTED:", len(ids))
    print("VIDEOS_RETURNED:", len(returned))
    for video_id, expected in EXPECTED.items():
        item = returned.get(video_id)
        print("\nVIDEO_ID:", video_id)
        if item is None:
            print("STATUS: NOT_RETURNED_BY_API")
            failures.append(video_id)
            continue
        snippet = item.get("snippet") or {}
        actual = extract_performers(snippet.get("description") or "")
        print("TITLE:", snippet.get("title", ""))
        print("DESCRIPTION_RETRIEVED:", "yes" if snippet.get("description") else "no_or_empty")
        print("PERFORMERS_COUNT:", len(actual) if actual else 0)
        print("PERFORMERS_JSON:", json.dumps(actual, ensure_ascii=False))
        if actual != expected:
            print("EXPECTED_JSON:", json.dumps(expected, ensure_ascii=False))
            failures.append(video_id)
            print("CHECK: FAIL")
        else:
            print("CHECK: PASS")
    print("\nTEST_RESULT:", "PASS" if not failures else "REVIEW_REQUIRED")
    if failures:
        print("FAILED_VIDEO_IDS:", json.dumps(failures, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
