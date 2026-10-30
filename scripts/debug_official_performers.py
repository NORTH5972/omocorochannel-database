import re
import urllib.request

URL = "https://omocoro.jp/video/"
TARGET = "R5V5SBGQtCs"
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=30) as response:
    html = response.read().decode("utf-8", errors="replace")

print("HTML_LENGTH", len(html))
for pattern in [TARGET, "writer", "ARuFa", "かんち", "performer", "author"]:
    print("COUNT", repr(pattern), html.count(pattern))

pos = html.find(TARGET)
if pos >= 0:
    print("TARGET_CONTEXT_BEGIN")
    print(html[max(0, pos-5000):pos+12000])
    print("TARGET_CONTEXT_END")

print("WRITER_HREFS_BEGIN")
for match in re.finditer(r'''href=["']([^"']*writer[^"']*)["']''', html, re.I):
    print(match.group(1))
print("WRITER_HREFS_END")
