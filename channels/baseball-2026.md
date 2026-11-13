# Baseball viewing options (2026)

The daily playlist generator now prioritizes public streams for Fubo Sports Network, NBC Sports NOW, CBS Sports Golazo Network, and beIN SPORTS XTRA, when ffprobe validates the media. These are general sports networks, not guaranteed MLB game broadcasters.

For live MLB games, use licensed sources:
- Yankees: YES / Gotham Sports / selected Prime Video games: https://www.yesnetwork.com/
- Mets: SNY / SNY on MLB / selected PIX11 games: https://sny.tv/
- MLB.TV: https://www.mlb.com/live-stream-games/
- MLB Network: https://www.mlb.com/network
- Official 2026 team viewing guide: https://www.mlb.com/news/how-to-watch-every-mlb-team-in-2026

Official websites are not direct M3U streams. Subscription and blackout restrictions may apply.

Run GitHub Actions workflow refresh-playlist.yml to validate and publish streams to playlists/sports.m3u. The URL stays the same. The playlist is unchanged until a successful run.
