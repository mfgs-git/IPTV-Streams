#!/usr/bin/env python3
"""Refresh curated public channel URLs without requiring network playback probes.
Sources: iptv-org public US streams listing. No unauthorized premium feeds.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import json
import re

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
URL="https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u"
out=Path("playlists/sports.m3u")
report=Path("playlists/validation-report.json")
def main():
    req=Request(URL,headers={"User-Agent":"Mozilla/5.0"})
    with urlopen(req,timeout=35) as r:
        lines=r.read().decode("utf-8-sig").splitlines()
    chosen={}
    meta=None
    for line in lines:
        line=line.strip()
        if line.startswith("#EXTINF:"):
            meta=line
        elif line.startswith("#EXTVLCOPT:"):
            continue
        elif line and not line.startswith("#"):
            if meta and line.startswith("https://") and ".m3u8" in line.lower():
                match=re.search(r'tvg-id="([^"]+)"',meta)
                channel_id=match.group(1).split("@")[0] if match else ""
                if channel_id in ALLOW and channel_id not in chosen:
                    name=meta.split(",",1)[-1].strip()
                    if "[Geo-blocked]" not in name:
                        chosen[channel_id]=(name,ALLOW[channel_id],line)
            meta=None
    if not chosen:
        raise SystemExit("No curated streams found; existing playlist preserved.")
    output=["#EXTM3U", "\"# SPORT TV PORTUGAL — channel directory, not direct streams", "# SPORT TV+ (free-to-air via Portuguese TV providers) — https://www.sporttv.pt/", "# SPORT TV 1 — subscription required", "# SPORT TV 2 — subscription required", "# SPORT TV 3 — subscription required", "# SPORT TV 4 — subscription required", "# SPORT TV 5 — subscription required", "# SPORT TV 6 — subscription required", "# SPORT TV 7 — subscription required", "# Official viewing and operator login: https://www.sporttv.pt/perguntas-frequentes/", "# No authorized public direct M3U URLs established; these entries are comments, not playable channels.\"", "# Curated public stream listings; playback NOT independently verified."]
    for name,group,url in chosen.values():
        output += [f'#EXTINF:-1 group-title="{group}",{name}',url]
    out.write_text("\n".join(output)+"\n",encoding="utf-8")
    report.write_text(json.dumps({"updated_at_utc":datetime.now(timezone.utc).isoformat(),"published":len(chosen),"validation":"not performed; source-listing only","note":"Stream availability and iOS playback are not guaranteed."},indent=2)+"\n",encoding="utf-8")
    print("Published",len(chosen),"curated entries (unverified)")
if __name__=="__main__":
    main()
