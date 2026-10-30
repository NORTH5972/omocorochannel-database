#!/usr/bin/env python3
"""Collect public playlists and their video entries for the official channel."""
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://www.googleapis.com/youtube/v3"
CHANNEL_ID = "UCOx-oLP9tOhiYwSK_m-yVxA"
OUTPUT = Path("data/playlists.json")
API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()


def api_get(resource, params):
    query = urllib.parse.urlencode({**params, "key": API_KEY})
    request = urllib.request.Request(
        f"{API_BASE}/{resource}?{query}",
        headers={"User-Agent": "OmocoroVideoDatabase/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def thumbnail(item):
    thumbs = item.get("thumbnails") or {}
    for key in ("maxres", "standard", "high", "medium", "default"):
        if thumbs.get(key, {}).get("url"):
            return thumbs[key]["url"]
    return ""


def collect_playlists():
    playlists = []
    token = None
    while True:
        params = {
            "part": "snippet,contentDetails",
            "channelId": CHANNEL_ID,
            "maxResults": 50,
        }
        if token:
            params["pageToken"] = token
        payload = api_get("playlists", params)
        for item in payload.get("items", []):
            snippet = item.get("snippet") or {}
            playlist_id = item.get("id")
            if not playlist_id:
                continue
            videos = []
            item_token = None
            while True:
                item_params = {
                    "part": "snippet,contentDetails",
                    "playlistId": playlist_id,
                    "maxResults": 50,
                }
                if item_token:
                    item_params["pageToken"] = item_token
                item_payload = api_get("playlistItems", item_params)
                for entry in item_payload.get("items", []):
                    entry_snippet = entry.get("snippet") or {}
                    resource = entry_snippet.get("resourceId") or {}
                    video_id = resource.get("videoId")
                    if not video_id:
                        continue
                    videos.append({
                        "id": video_id,
                        "title": entry_snippet.get("title") or "タイトル未取得",
                        "thumbnailUrl": thumbnail(entry_snippet),
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                    })
                item_token = item_payload.get("nextPageToken")
                if not item_token:
                    break
                time.sleep(0.1)

            playlists.append({
                "id": playlist_id,
                "title": snippet.get("title") or "タイトル未設定",
                "description": snippet.get("description") or "",
                "thumbnailUrl": thumbnail(snippet),
                "url": f"https://www.youtube.com/playlist?list={playlist_id}",
                "videoCount": len(videos),
                "videos": videos,
            })
            print(f"Collected playlist: {snippet.get('title', playlist_id)} ({len(videos)} videos)")
        token = payload.get("nextPageToken")
        if not token:
            break
        time.sleep(0.1)
    return playlists


def main():
    if not API_KEY:
        raise SystemExit("YOUTUBE_API_KEY is not set. Add it to GitHub Actions secrets.")
    playlists = collect_playlists()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(playlists, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(playlists)} official playlists to {OUTPUT}")


if __name__ == "__main__":
    main()
