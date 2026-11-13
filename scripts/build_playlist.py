#!/usr/bin/env python3
"""Build a flat M3U from public IPTV-org category playlists."""
from urllib.request import Request, urlopen
from pathlib import Path
import re
CATEGORIES = ("sports", "movies", "classic", "series", "entertainment", "comedy")
output = ["#EXTM3U"]
seen = set()
for category in CATEGORIES:
    try:
        req = Request("https://iptv-org.github.io/iptv/categories/"+category+".m3u", headers={"User-Agent":"IPTV-Streams-playlist-builder/1.0"})
        with urlopen(req, timeout=35) as response:
            lines = response.read().decode("utf-8-sig").splitlines()
    except Exception as exc:
        print("Failed", category, exc)
        continue
    pending = None
    count = 0
    for raw in lines:
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            pending = line
        elif line and not line.startswith("#"):
            if pending and re.match(r"^https?://",line) and not re.search(r"\.m3u(?:\?|$)",line,re.I) and line not in seen:
                output.extend((pending,line))
                seen.add(line)
                count += 1
            pending = None
    print(category, count)
if len(output) <= 1:
    raise SystemExit("No streams retrieved; refusing to overwrite sports.m3u")
Path("playlists/sports.m3u").write_text("\n".join(output)+"\n", encoding="utf-8")
print("Total:",len(seen))
