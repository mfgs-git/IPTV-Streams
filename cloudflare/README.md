# Private OpenIPTV gateway (Cloudflare Worker)

This folder provides an Xtream Codes-compatible **live-channel** API backed by the private GitHub file `playlists/sports.m3u`. The GitHub repository stays private. The Worker address stays the same across playlist refreshes.

## Deploy

1. Log in to Cloudflare Dashboard → **Workers & Pages** → **Create** → **Worker**. Name it `private-iptv-gateway`. Deploy it.
2. Edit the Worker code and replace it with [worker.js](worker.js), then deploy. Alternatively, from this repository's `cloudflare` directory use Wrangler CLI (`npx wrangler deploy`) after `npx wrangler login`.
3. In the Worker's **Settings → Variables and Secrets**, add these **encrypted secrets** (not plain text variables):
   - `GITHUB_TOKEN`: fine-grained GitHub personal access token, restricted to repository `mfgs-git/IPTV-Streams`, with **Contents: Read-only** permission.
   - `XTREAM_USERNAME`: a new unique gateway username (not your GitHub username).
   - `XTREAM_PASSWORD`: a long, randomly generated gateway password (not your GitHub password).
4. In a browser visit `https://private-iptv-gateway.<your-workers-subdomain>.workers.dev/health`. You should see a ready response. **This is only a health check, not evidence the playlist works.**
5. Test the API by visiting `https://<your-worker-domain>/player_api.php?username=<username>&password=<password>&action=get_live_categories` in a private browser window. It should return categories. Be aware that Xtream clients send credentials in URLs, so browser history, logs and screenshots can expose them. Do not share these links.
6. In OpenIPTV → **Sources → Add → Xtream Codes**, enter:
   - Name: `Private IPTV`
   - Server URL: `https://private-iptv-gateway.<your-workers-subdomain>.workers.dev` (replace with your actual Worker domain; no path)
   - Username: your `XTREAM_USERNAME`
   - Password: your `XTREAM_PASSWORD`
7. If your player prefers M3U URL mode, the authenticated URL is `https://<your-worker-domain>/get.php?username=<username>&password=<password>&type=m3u_plus&output=m3u8`. Keep this URL private.

## How it works

- The gateway fetches the **current** `playlists/sports.m3u` file through the GitHub API with a read-only token.
- It exposes live categories and live streams through common Xtream Codes endpoints.
- Each live-stream endpoint **redirects** the player to the public stream host. The Worker does not bypass geo-restrictions, DRM, unsupported codecs, or a stream provider's access rules.
- The same Worker URL continues to work after GitHub Actions refreshes the playlist.
- It does not host, rebroadcast, or decrypt premium streams. Only use streams you are authorized to access.
- The gateway is a **compatibility implementation**, not a full Xtream Codes server; some player features (EPG, VOD, catch-up) are not supported.
- **Security caveat:** Xtream Codes authentication commonly transmits credentials in URL parameters or paths. Use unique credentials and HTTPS, and avoid forwarding/logging full URLs.
- The GitHub Actions playlist generator must first complete successfully. The existing `sports.m3u` file still contains nested directory links until then; the gateway will not convert those into playable channels.

## Troubleshooting

- `401`: username/password mismatch.
- `502`: GitHub token/permissions, invalid M3U, or GitHub access issue. Check Worker logs.
- Empty categories: playlist refresh has not produced direct channel entries.
- Playback errors: upstream stream is unavailable, blocked in your region, or incompatible with the app. A passing GitHub ffprobe check does not guarantee iPhone playback.
- `404` on stream: stream no longer exists in the latest playlist.
