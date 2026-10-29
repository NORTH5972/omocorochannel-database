#!/usr/bin/env python3
"""Enrich performer names only when an exact-title match is found on Omocoro's official video archive."""
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

DATA = Path("data/videos.json")
BASE = "https://omocoro.jp/video/"
MAX_PAGES = 121
KNOWN_NAMES = [
    "ダ・ヴィンチ・恐山", "モンゴルナイフ", "山口むつお", "みくのしん",
    "マンスーン", "ヤスミノ", "ギャラクシー", "ARuFa", "かまど",
    "永田", "原宿", "加藤 亮", "加藤亮", "加藤", "恐山",
]


def clean(value):
    value = unicodedata.normalize("NFKC", value or "").lower()
    return re.sub(r"[\s　]+", "", value)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; OmocoroVideoIndex/1.0; +https://github.com/NORTH5972/omocorochannel-database)"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read()


def main():
    videos = json.loads(DATA.read_text(encoding="utf-8"))
    by_title = {}
    for video in videos:
        title = clean(video.get("title", ""))
        if title:
            by_title.setdefault(title, []).append(video)

    matched = 0
    pages_with_cards = 0
    empty_pages = 0
    for page_no in range(1, MAX_PAGES + 1):
        url = BASE if page_no == 1 else f"{BASE}page/{page_no}/"
        try:
            html = fetch(url)
        except urllib.error.HTTPError as exc:
            print(f"Archive page {page_no}: HTTP {exc.code}; stopping.")
            break
        except Exception as exc:
            print(f"Archive page {page_no}: {type(exc).__name__}: {exc}; stopping.")
            break

        soup = BeautifulSoup(html, "html.parser")
        # The archive uses article cards; use them as the matching scope to avoid
        # accidentally combining names from different video entries.
        cards = soup.find_all("article")
        if not cards:
            cards = soup.select("li, .video-item, .archive-item, .post-item")
        page_matches = 0
        for card in cards:
            card_text = card.get_text(" ", strip=True)
            if not card_text:
                continue
            card_titles = []
            for a in card.find_all("a", href=True):
                title = clean(a.get_text(" ", strip=True))
                if title in by_title:
                    card_titles.extend(by_title[title])
            if not card_titles:
                # Fallback: match a normalized known title as a substring of card text.
                normalized_card = clean(card_text)
                for title, found in by_title.items():
                    if title and len(title) >= 8 and title in normalized_card:
                        card_titles.extend(found)
            if not card_titles:
                continue

            people = []
            for a in card.find_all("a", href=True):
                href = a.get("href", "")
                name = a.get_text(" ", strip=True)
                if ("/writer/" in href or "/author/" in href) and name:
                    if name not in ("オモコロチャンネル", "オモコロ編集部") and name not in people:
                        people.append(name)
            if not people:
                people = [name for name in KNOWN_NAMES if name in card_text]
            # Avoid assigning tags if we could not find an explicit name on the official card.
            if not people:
                continue
            for video in card_titles:
                current = video.get("performers") or []
                combined = list(dict.fromkeys(current + people))
                if combined != current:
                    video["performers"] = combined
                    video["reviewStatus"] = "出演者候補：オモコロ公式アーカイブ照合"
                    video["source"] = "YouTubeチャンネル一覧 + オモコロ公式動画アーカイブ"
                    matched += 1
                    page_matches += 1
        if cards:
            pages_with_cards += 1
        if page_matches == 0:
            empty_pages += 1
        else:
            empty_pages = 0
        print(f"Archive page {page_no}: cards={len(cards)}, matched_updates={page_matches}")
        if empty_pages >= 5:
            print("Five consecutive pages had no new matches; stopping.")
            break
        time.sleep(0.25)

    DATA.write_text(json.dumps(videos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tagged = sum(1 for video in videos if video.get("performers"))
    print(f"Performer enrichment updates: {matched}; videos with performer tags: {tagged}/{len(videos)}; archive pages checked: {pages_with_cards}")


if __name__ == "__main__":
    main()
