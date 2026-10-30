#!/usr/bin/env python3
"""Replace performer tags with names credited by Omocoro's official video archive."""
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

OUTPUT = Path("data/videos.json")
BASE = "https://omocoro.jp/video/"

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.href = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data):
        if self.href is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join(" ".join(self.parts).split())))
            self.href = None
            self.parts = []

def video_id(url):
    p = urlparse(url)
    value = ""
    if p.netloc.endswith("youtu.be"):
        value = p.path.strip("/").split("/")[0]
    elif p.netloc.endswith("youtube.com") or p.netloc.endswith("youtube-nocookie.com"):
        value = parse_qs(p.query).get("v", [""])[0]
        if not value and "/embed/" in p.path:
            value = p.path.split("/embed/", 1)[1].split("/")[0]
    return value if re.fullmatch(r"[A-Za-z0-9_-]{11}", value or "") else ""

def main():
    pages = [BASE]
    seen = set()
    credits = {}
    while pages and len(seen) < 100:
        page = pages.pop(0)
        if page in seen:
            continue
        seen.add(page)
        req = urllib.request.Request(page, headers={"User-Agent": "Mozilla/5.0 OmocoroArchiveIndexer/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
        parser = Parser()
        parser.feed(html)
        current = None
        names = []
        for href, label in parser.links:
            absolute = urljoin(page, href or "")
            path = urlparse(absolute).path
            found_id = video_id(absolute)
            if found_id:
                if current and names:
                    credits[current] = names
                current, names = found_id, []
            elif current and "/writer/" in path and label and label not in names:
                names.append(label)
            if re.search(r"/video/page/\d+/?$", path) and absolute not in seen and absolute not in pages:
                pages.append(absolute)
        if current and names:
            credits[current] = names
        print(f"Scanned {page}; credited videos so far: {len(credits)}")

    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    changed = 0
    for item in data:
        key = str(item.get("id") or item.get("videoId") or "")
        if key in credits:
            item["performers"] = credits[key]
            item["performerSource"] = "オモコロ公式動画アーカイブ"
            item["reviewStatus"] = "出演者：公式アーカイブ照合済み"
            changed += 1
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Official archive performer tags updated: {changed}/{len(data)} videos; archive credits: {len(credits)}")

if __name__ == "__main__":
    main()
