#!/usr/bin/env python3
"""Create a flat IPTV playlist containing only streams that pass a media probe.

Run with Python 3.12 and ffprobe installed. Only public IPTV-org listings are used.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
import json
import os
import re
import subprocess

CATEGORIES = ("sports", "news", "movies", "classic", "series", "entertainment", "comedy")
BASE = "https://iptv-org.github.io/iptv/categories/"
MAX_WORKERS = 16
PROBE_TIMEOUT = 12
MAX_CANDIDATES = int(os.environ.get("MAX_CANDIDATES", "3000"))
OUT = Path("playlists/sports.m3u")
REPORT = Path("playlists/validation-report.json")


def fetch(category):
    req = Request(BASE + category + ".m3u", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=35) as resp:
        return resp.read().decode("utf-8-sig", errors="replace")


def parse(text, category):
    entries = []
    pending = None
    options = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            pending = line
            options = []
        elif line.startswith("#EXTVLCOPT:") and pending:
            options.append(line)
        elif line and not line.startswith("#"):
            if pending and urlsplit(line).scheme in ("http", "https"):
                if not re.search(r"\.m3u(?:\?|$)", line, re.I):
                    entries.append((category, pending, tuple(options), line))
            pending = None
            options = []
    return entries


def verify(entry):
    category, meta, options, url = entry
    # ffprobe checks for a real audio or video stream, not just an HTTP status.
    # Reject URLs that only return HTML, errors or another M3U directory.
    cmd = [
        "ffprobe", "-v", "error",
        "-analyzeduration", "2000000", "-probesize", "2000000",
        "-show_entries", "stream=codec_type", "-of", "json", url
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=PROBE_TIMEOUT)
        if p.returncode != 0:
            return None
        data = json.loads(p.stdout)
        if not any(s.get("codec_type") in ("audio", "video") for s in data.get("streams", [])):
            return None
        return entry
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return None


def main():
    candidates = []
    source_errors = {}
    for category in CATEGORIES:
        try:
            found = parse(fetch(category), category)
            candidates.extend(found)
            print(f"{category}: {len(found)} candidates", flush=True)
        except Exception as exc:
            source_errors[category] = str(exc)
            print(f"{category}: fetch failed: {exc}", flush=True)

    # Prefer sports and news; preserve source ordering.
    unique = []
    seen = set()
    for entry in candidates:
        url = entry[3]
        if url not in seen:
            seen.add(url)
            unique.append(entry)
    unique = unique[:MAX_CANDIDATES]
    accepted = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        jobs = {pool.submit(verify, entry): entry for entry in unique}
        for future in as_completed(jobs):
            result = future.result()
            if result:
                accepted.append(result)
    # Restore category/source order after parallel validation.
    positions = {entry[3]: i for i, entry in enumerate(unique)}
    accepted.sort(key=lambda entry: positions[entry[3]])

    if not accepted:
        raise SystemExit("Zero playable streams verified; existing playlist preserved.")
    lines = ["#EXTM3U"]
    per_category = {}
    for category, meta, options, url in accepted:
        per_category[category] = per_category.get(category, 0) + 1
        # Ensure every entry has a category even if upstream metadata omits it.
        if 'group-title="' not in meta:
            meta = meta.replace(",", f' group-title="{category.title()}",', 1)
        lines.extend([meta, *options, url])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(unique),
        "passed": len(accepted),
        "failed": len(unique) - len(accepted),
        "by_category": per_category,
        "source_errors": source_errors,
        "test": "ffprobe confirms audio or video stream from GitHub Actions runner",
        "limitations": "Passing does not guarantee browser CORS support, future uptime, or availability in other regions."
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
