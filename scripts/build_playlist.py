#!/usr/bin/env python3
"""Add newly listed public sports streams without deleting prior entries or channel notes.
Listings are not independently playback-validated. Paid channels require provider access.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import json, re

ALLOW = {
 "beINSPORTSXTRA.us": "Sports",
 "FuboSportsNetwork.us": "Sports",
 "NBCSportsNOW.us": "Sports",
 "CBSSportsGolazoNetwork.us": "Sports",
 "FTFSports.us": "Sports",
 "NBCNewsNOW.us": "News",
 "FoxWeather.us": "News",
 "BloombergTV.us": "News",
 "CourtTV.us": "News",
 "NewsmaxTV.us": "News",
}
URL = "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u"
OUT = Path("playlists/sports.m3u")
REPORT = Path("playlists/validation-report.json")

def main():
    original = OUT.read_text(encoding="utf-8") if OUT.exists() else "#EXTM3U\n"
    if not original.startswith("#EXTM3U"):
        raise SystemExit("Existing playlist invalid; preserving it.")
    existing_urls = {x.strip() for x in original.splitlines() if x.strip().startswith(("http://", "https://"))}
    request = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=35) as response:
        source = response.read().decode("utf-8-sig", errors="replace")
    added = []
    pending = None
    for line in source.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            pending = line
        elif line.startswith("#"):
            continue
        elif line:
            if pending and line.startswith("https://") and ".m3u8" in line.lower() and line not in existing_urls:
                m = re.search(r'tvg-id="([^"]+)"', pending)
                cid = m.group(1).split("@")[0] if m else ""
                if cid in ALLOW and "[Geo-blocked]" not in pending:
                    name = pending.split(",", 1)[-1].strip()
                    added.extend([f'#EXTINF:-1 group-title="{ALLOW[cid]}",{name}', line])
                    existing_urls.add(line)
            pending = None
    if added:
        OUT.write_text(original.rstrip("\n") + "\n" + "\n".join(added) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps({
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "new_entries": len(added)//2,
        "total_entries": (original.count("#EXTINF:") + len(added)//2),
        "validation": "Not performed; URLs from public source listing",
        "notes": "Existing channels and SPORT TV/NY sports reference comments preserved."
    }, indent=2) + "\n", encoding="utf-8")
    print("Added", len(added)//2, "streams; previous entries preserved")

if __name__ == "__main__":
    main()
