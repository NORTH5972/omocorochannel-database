#!/usr/bin/env python3
"""Match performers from the official Omocoro video archive, when the card is unambiguous."""
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
MAX_PAGES = 120
KNOWN_NAMES = [
    "ダ・ヴィンチ・恐山", "モンゴルナイフ", "山口むつお", "みくのしん",
    "マンスーン", "ヤスミノ", "ギャラクシー", "ARuFa", "かまど",
    "永田", "原宿", "加藤 亮", "加藤亮",
]


def clean(value):
    value = unicodedata.normalize("NFKC", value or "").lower()
    return re.sub(r"[\s　]+", "", value)


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; OmocoroVideoIndex/1.0; +https://github.com/NORTH5972/omocorochannel-database)"},
    )
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
    dates_updated = 0
    pages_with_matches = 0
    empty_pages = 0
    for page_no in range(1, MAX_PAGES + 1):
        url = BASE if page_no == 1 else f"{BASE}page/{page_no}/"
        try:
            soup = BeautifulSoup(fetch(url), "html.parser")
        except urllib.error.HTTPError as exc:
            print(f"Archive page {page_no}: HTTP {exc.code}; stopping.")
            break
        except Exception as exc:
            print(f"Archive page {page_no}: {type(exc).__name__}: {exc}; stopping.")
            break

        page_matches = 0
        page_dates = 0
        for anchor in soup.find_all("a", href=True):
            title = clean(anchor.get_text(" ", strip=True))
            if title not in by_title:
                continue
            href = anchor.get("href", "")
            if not ("youtu.be/" in href or "youtube.com/watch" in href):
                continue

            people = []
            published_date = ""
            # Walk from the title link outward and use the smallest container that
            # contains exactly one YouTube link plus identifiable names.
            parent = anchor
            for _ in range(9):
                parent = parent.parent
                if parent is None:
                    break
                yt_links = [
                    item for item in parent.find_all("a", href=True)
                    if "youtu.be/" in item.get("href", "") or "youtube.com/watch" in item.get("href", "")
                ]
                if len(yt_links) != 1:
                    continue
                card_text = parent.get_text(" ", strip=True)
                date_match = re.search(r"(?<!\d)(20\d{2})[./年\-]\s*(\d{1,2})[./月\-]\s*(\d{1,2})日?", card_text)
                if date_match and not published_date:
                    year, month, day = date_match.groups()
                    published_date = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
                for item in parent.find_all("a", href=True):
                    item_href = item.get("href", "")
                    name = item.get_text(" ", strip=True)
                    if ("/writer/" in item_href or "/author/" in item_href) and name:
                        if name not in ("オモコロチャンネル", "オモコロ編集部") and name not in people:
                            people.append(name)
                if not people:
                    text = parent.get_text(" ", strip=True)
                    people = [name for name in KNOWN_NAMES if name in text]
                if people:
                    break

            for video in by_title[title]:
                if published_date and not video.get("publishedAt"):
                    video["publishedAt"] = published_date
                    dates_updated += 1
                    page_dates += 1
                if not people:
                    continue
                current = video.get("performers") or []
                combined = list(dict.fromkeys(current + people))
                if combined != current:
                    video["performers"] = combined
                    video["reviewStatus"] = "出演者候補：オモコロ公式アーカイブ照合"
                    video["source"] = "YouTubeチャンネル一覧 + オモコロ公式動画アーカイブ"
                    matched += 1
                    page_matches += 1

        if page_matches:
            pages_with_matches += 1
        if page_matches or page_dates:
            empty_pages = 0
        else:
            empty_pages += 1
        print(f"Archive page {page_no}: performer matches updated={page_matches}; publication dates added={page_dates}")
        if empty_pages >= 5:
            print("Five consecutive pages had no new matches; stopping.")
            break
        time.sleep(0.25)

    DATA.write_text(json.dumps(videos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tagged = sum(1 for video in videos if video.get("performers"))
    print(f"Performer enrichment updates: {matched}; publication dates added: {dates_updated}; videos with performer tags: {tagged}/{len(videos)}; pages with matches: {pages_with_matches}")


if __name__ == "__main__":
    main()
