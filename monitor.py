#!/usr/bin/env python3
"""
Album release monitor for 'mecore' by low_battery
Checks music platforms every hour via GitHub Actions and updates the dashboard.
"""

import requests
import json
import os
import re
from datetime import datetime, timezone

ALBUM = "mecore"
ARTIST = "low_battery"
ARTIST_DISPLAY = "low_battery"
ALBUM_DISPLAY = "mecore"
SPOTIFY_LINK = "https://open.spotify.com/album/6YYc7yRKfMUyvGzw1sXoRT"

STATUS_FILE = "status.json"
HTML_FILE = "index.html"

HA_URL = os.environ.get("HA_URL", "").rstrip("/")
HA_TOKEN = os.environ.get("HA_TOKEN", "")
HA_NOTIFY_SERVICE = "mobile_app_pixel_9_pro_xl"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


# ─── Platform checkers ────────────────────────────────────────────────────────

def check_apple_music():
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": f"{ALBUM} {ARTIST}", "entity": "album", "limit": 10},
            timeout=10,
        )
        for result in r.json().get("results", []):
            name = result.get("collectionName", "").lower()
            artist = result.get("artistName", "").lower()
            if ALBUM in name and ("low" in artist or "battery" in artist):
                cid = result["collectionId"]
                return True, f"https://music.apple.com/album/{cid}"
    except Exception:
        pass
    return False, None


def check_deezer():
    try:
        r = requests.get(
            "https://api.deezer.com/search/album",
            params={"q": f'artist:"{ARTIST}" album:"{ALBUM}"'},
            timeout=10,
        )
        for result in r.json().get("data", []):
            title = result.get("title", "").lower()
            artist_name = result.get("artist", {}).get("name", "").lower()
            if ALBUM in title and ("low" in artist_name or "battery" in artist_name):
                return True, f"https://www.deezer.com/album/{result['id']}"
    except Exception:
        pass
    return False, None


def check_iheart():
    try:
        r = requests.get(
            "https://api2.iheart.com/api/v3/search/all",
            params={"keywords": f"{ALBUM} {ARTIST}", "maxRows": 10, "startIndex": 0},
            timeout=10,
        )
        albums = r.json().get("albums", {}).get("hits", [])
        for album in albums:
            name = album.get("title", "").lower()
            artist_name = album.get("artistName", "").lower()
            if ALBUM in name and ("low" in artist_name or "battery" in artist_name):
                return True, f"https://www.iheart.com/search/?keywords={ALBUM}+{ARTIST}"
    except Exception:
        pass
    return False, None


def check_pandora():
    try:
        r = requests.get(
            f"https://www.pandora.com/search/{ALBUM}%20{ARTIST}/albums",
            headers=HEADERS,
            timeout=10,
        )
        text_lower = r.text.lower()
        if ALBUM in text_lower and ("low_battery" in text_lower or "low battery" in text_lower):
            return True, f"https://www.pandora.com/search/{ALBUM}+{ARTIST}/albums"
    except Exception:
        pass
    return False, None


def check_tidal():
    # Try open API first
    try:
        r = requests.get(
            "https://openapi.tidal.com/search",
            params={
                "query": f"{ALBUM} {ARTIST}",
                "type": "ALBUMS",
                "offset": 0,
                "limit": 10,
                "countryCode": "US",
            },
            headers={"accept": "application/vnd.tidal.v1+json"},
            timeout=10,
        )
        if r.status_code == 200:
            for item in r.json().get("albums", {}).get("items", []):
                if ALBUM in item.get("title", "").lower():
                    return True, f"https://listen.tidal.com/album/{item.get('id')}"
    except Exception:
        pass
    # Fallback: scrape search page
    try:
        r = requests.get(
            f"https://listen.tidal.com/search?q={ALBUM}+{ARTIST}",
            headers=HEADERS,
            timeout=10,
        )
        if ALBUM in r.text.lower() and ("low_battery" in r.text.lower() or "low battery" in r.text.lower()):
            return True, f"https://listen.tidal.com/search?q={ALBUM}+{ARTIST}"
    except Exception:
        pass
    return False, None


def check_amazon_music():
    try:
        r = requests.get(
            f"https://music.amazon.com/search/{ALBUM}+{ARTIST}",
            headers=HEADERS,
            timeout=10,
        )
        text_lower = r.text.lower()
        if ALBUM in text_lower and ("low_battery" in text_lower or "low battery" in text_lower):
            return True, f"https://music.amazon.com/search/{ALBUM}+{ARTIST}"
    except Exception:
        pass
    return False, None


def check_youtube_music():
    try:
        r = requests.get(
            "https://music.youtube.com/search",
            params={"q": f"{ALBUM} {ARTIST}"},
            headers=HEADERS,
            timeout=10,
        )
        text_lower = r.text.lower()
        if ALBUM in text_lower and ("low_battery" in text_lower or "low battery" in text_lower):
            return True, f"https://music.youtube.com/search?q={ALBUM}+{ARTIST}"
    except Exception:
        pass
    return False, None


def check_soundcloud():
    try:
        r = requests.get(
            "https://soundcloud.com/search/albums",
            params={"q": f"{ALBUM} {ARTIST}"},
            headers=HEADERS,
            timeout=10,
        )
        text_lower = r.text.lower()
        if ALBUM in text_lower and ("low_battery" in text_lower or "low battery" in text_lower):
            return True, f"https://soundcloud.com/search/albums?q={ALBUM}+{ARTIST}"
    except Exception:
        pass
    return False, None


def check_audiomack():
    try:
        r = requests.get(
            "https://audiomack.com/api/v1/music/search",
            params={"q": f"{ALBUM} {ARTIST}", "type": "album"},
            headers=HEADERS,
            timeout=10,
        )
        for item in r.json().get("results", {}).get("album", []):
            if ALBUM in item.get("title", "").lower():
                return True, f"https://audiomack.com/search?q={ALBUM}+{ARTIST}"
    except Exception:
        pass
    return False, None


def check_boomplay():
    try:
        r = requests.get(
            f"https://www.boomplay.com/search/default/{ALBUM}+{ARTIST}",
            headers=HEADERS,
            timeout=10,
        )
        text_lower = r.text.lower()
        if ALBUM in text_lower and ("low_battery" in text_lower or "low battery" in text_lower):
            return True, f"https://www.boomplay.com/search/default/{ALBUM}+{ARTIST}"
    except Exception:
        pass
    return False, None


def check_anghami():
    try:
        r = requests.get(
            "https://play.anghami.com/search",
            params={"q": f"{ALBUM} {ARTIST}"},
            headers=HEADERS,
            timeout=10,
        )
        if ALBUM in r.text.lower():
            return True, f"https://play.anghami.com/search?q={ALBUM}+{ARTIST}"
    except Exception:
        pass
    return False, None


def check_jiosaavn():
    try:
        r = requests.get(
            "https://www.jiosaavn.com/api.php",
            params={
                "q": f"{ALBUM} {ARTIST}",
                "__call": "search.getAlbumResults",
                "_format": "json",
                "_marker": "0",
            },
            headers=HEADERS,
            timeout=10,
        )
        for item in r.json().get("results", []):
            if ALBUM in item.get("title", "").lower():
                return True, f"https://www.jiosaavn.com/search/album/{ALBUM}"
    except Exception:
        pass
    return False, None


def check_napster():
    try:
        r = requests.get(
            "https://api.napster.com/v2.2/search",
            params={
                "query": f"{ALBUM} {ARTIST}",
                "type": "album",
                "per_type_limit": 5,
                "apikey": "Y2VkOTMxMzItMDc4Zi00ZTQ2LWJmNDYtNWQ0MDkzZDdjZTBm",
            },
            timeout=10,
        )
        albums = r.json().get("search", {}).get("data", {}).get("albums", [])
        for album in albums:
            if ALBUM in album.get("name", "").lower():
                return True, "https://us.napster.com/search#track?q=mecore+low_battery"
    except Exception:
        pass
    return False, None


def check_shazam():
    try:
        r = requests.get(
            "https://apple.shazam.com/search/apple/en/US/web/search",
            params={"q": f"{ALBUM} {ARTIST}"},
            headers=HEADERS,
            timeout=10,
        )
        if ALBUM in r.text.lower() and ("low_battery" in r.text.lower() or "low battery" in r.text.lower()):
            return True, f"https://www.shazam.com/search?q={ALBUM}+{ARTIST}"
    except Exception:
        pass
    return False, None


def check_beatport():
    try:
        r = requests.get(
            "https://www.beatport.com/search/releases",
            params={"q": f"{ALBUM} {ARTIST}"},
            headers=HEADERS,
            timeout=10,
        )
        text_lower = r.text.lower()
        if ALBUM in text_lower and ("low_battery" in text_lower or "low battery" in text_lower):
            return True, f"https://www.beatport.com/search/releases?q={ALBUM}+{ARTIST}"
    except Exception:
        pass
    return False, None


# ─── Platform registry ────────────────────────────────────────────────────────

# Platforms we can check automatically
CHECKABLE = {
    "Apple Music": check_apple_music,
    "Deezer": check_deezer,
    "iHeartRadio": check_iheart,
    "Pandora": check_pandora,
    "Tidal": check_tidal,
    "Amazon Music": check_amazon_music,
    "YouTube Music": check_youtube_music,
    "SoundCloud": check_soundcloud,
    "Audiomack": check_audiomack,
    "Boomplay": check_boomplay,
    "Anghami": check_anghami,
    "JioSaavn": check_jiosaavn,
    "Napster": check_napster,
    "Shazam": check_shazam,
    "Beatport": check_beatport,
}

# Platforms that are regional or auto-indexed (can't be auto-checked)
REGIONAL = [
    "NetEase Cloud Music",
    "QQ Music",
    "KKBox",
    "Line Music",
    "AWA",
    "Melon",
    "Bugs Music",
    "Genie Music",
    "Gaana",
    "Wynk Music",
    "Claro Música",
    "Nuuday",
    "TikTok Music",
    "Facebook / Instagram",
    "Peloton",
    "Gracenote",
    "MediaNet",
    "Soundtrack by Twitch",
    "Resso",
    "7digital",
]


# ─── Status helpers ───────────────────────────────────────────────────────────

def load_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE) as f:
            return json.load(f)

    # First run — bootstrap with Spotify confirmed
    status = {
        "last_checked": None,
        "platforms": {
            "Spotify": {
                "status": "confirmed",
                "confirmed_at": datetime.now(timezone.utc).isoformat(),
                "link": SPOTIFY_LINK,
            }
        },
    }
    # Add all checkable platforms as pending
    for name in CHECKABLE:
        status["platforms"][name] = {"status": "pending", "confirmed_at": None, "link": None}
    # Add regional as manual
    for name in REGIONAL:
        status["platforms"][name] = {"status": "manual", "confirmed_at": None, "link": None}
    return status


def save_status(status):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)


# ─── HA notification ──────────────────────────────────────────────────────────

def notify_ha(platform_name, link):
    if not HA_URL or not HA_TOKEN:
        return
    try:
        msg = f"🎵 mecore by low_battery is now live on {platform_name}!"
        payload = {
            "title": "Album Monitor",
            "message": msg,
        }
        if link:
            payload["data"] = {"url": link}
        requests.post(
            f"{HA_URL}/api/services/notify/{HA_NOTIFY_SERVICE}",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        print(f"  → HA notification sent for {platform_name}")
    except Exception as e:
        print(f"  → HA notification failed: {e}")


# ─── Dashboard HTML generator ─────────────────────────────────────────────────

def generate_html(status):
    platforms = status["platforms"]
    confirmed = [n for n, v in platforms.items() if v["status"] == "confirmed"]
    pending = [n for n, v in platforms.items() if v["status"] == "pending"]
    manual = [n for n, v in platforms.items() if v["status"] == "manual"]
    total = len(platforms)
    count = len(confirmed)
    last_checked = status.get("last_checked") or "Never"
    if last_checked != "Never":
        try:
            dt = datetime.fromisoformat(last_checked)
            last_checked = dt.strftime("%d %b %Y, %H:%M UTC")
        except Exception:
            pass

    pct = round((count / total) * 100)

    def card(name, data):
        s = data["status"]
        link = data.get("link")
        confirmed_at = data.get("confirmed_at")
        date_str = ""
        if confirmed_at:
            try:
                dt = datetime.fromisoformat(confirmed_at)
                date_str = dt.strftime("%d %b %Y")
            except Exception:
                date_str = confirmed_at[:10]

        if s == "confirmed":
            icon = "✓"
            badge = "confirmed"
            href = f'href="{link}"' if link else f'href="https://open.spotify.com/album/6YYc7yRKfMUyvGzw1sXoRT"'
            tag = "a"
            extra = f'target="_blank" rel="noopener" {href}'
            sub = f'<span class="date">{date_str}</span>'
        elif s == "manual":
            icon = "◎"
            badge = "manual"
            tag = "div"
            extra = ""
            sub = '<span class="date">regional / manual</span>'
        else:
            icon = "○"
            badge = "pending"
            tag = "div"
            extra = ""
            sub = '<span class="date">checking hourly…</span>'

        return f"""
        <{tag} class="card {badge}" {extra}>
          <span class="icon">{icon}</span>
          <div class="card-body">
            <span class="platform-name">{name}</span>
            {sub}
          </div>
        </{tag}>"""

    all_cards = ""
    for name in sorted(confirmed):
        all_cards += card(name, platforms[name])
    for name in sorted(pending):
        all_cards += card(name, platforms[name])
    for name in sorted(manual):
        all_cards += card(name, platforms[name])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>mecore — Release Tracker</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #0d0d0f;
      color: #e0e0e0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      padding: 2rem 1rem 4rem;
    }}

    .hero {{
      max-width: 680px;
      margin: 0 auto 2.5rem;
      text-align: center;
    }}

    .album-title {{
      font-size: 3.5rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      background: linear-gradient(135deg, #1db954, #1ed760, #a0f0c0);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      line-height: 1.1;
    }}

    .artist-name {{
      font-size: 1.1rem;
      color: #888;
      margin-top: 0.4rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }}

    .spotify-btn {{
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      margin-top: 1.4rem;
      padding: 0.65rem 1.5rem;
      background: #1db954;
      color: #000;
      font-weight: 700;
      font-size: 0.9rem;
      border-radius: 500px;
      text-decoration: none;
      letter-spacing: 0.03em;
      transition: background 0.2s;
    }}
    .spotify-btn:hover {{ background: #1ed760; }}
    .spotify-btn svg {{ width: 18px; height: 18px; }}

    .progress-section {{
      max-width: 680px;
      margin: 0 auto 2.5rem;
    }}

    .progress-header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 0.6rem;
    }}

    .progress-label {{
      font-size: 0.85rem;
      color: #888;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}

    .progress-count {{
      font-size: 1.6rem;
      font-weight: 700;
      color: #fff;
    }}

    .progress-count span {{
      font-size: 1rem;
      color: #555;
      font-weight: 400;
    }}

    .bar-bg {{
      height: 6px;
      background: #222;
      border-radius: 3px;
      overflow: hidden;
    }}

    .bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, #1db954, #1ed760);
      border-radius: 3px;
      width: {pct}%;
      transition: width 1s ease;
    }}

    .last-checked {{
      font-size: 0.75rem;
      color: #444;
      margin-top: 0.6rem;
      text-align: right;
    }}

    .grid {{
      max-width: 680px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 0.75rem;
    }}

    .card {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.85rem 1rem;
      border-radius: 10px;
      background: #16161a;
      border: 1px solid #222;
      text-decoration: none;
      color: inherit;
      transition: border-color 0.2s, background 0.2s;
    }}

    .card.confirmed {{
      border-color: #1db95433;
      background: #0d1f14;
    }}
    .card.confirmed:hover {{
      border-color: #1db954;
      background: #0f2618;
    }}

    .card.pending {{
      opacity: 0.55;
    }}

    .card.manual {{
      opacity: 0.4;
    }}

    .icon {{
      font-size: 1.1rem;
      flex-shrink: 0;
      color: #1db954;
    }}
    .card.pending .icon, .card.manual .icon {{ color: #444; }}

    .card-body {{
      display: flex;
      flex-direction: column;
      gap: 0.1rem;
      min-width: 0;
    }}

    .platform-name {{
      font-size: 0.9rem;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .date {{
      font-size: 0.72rem;
      color: #555;
    }}
    .card.confirmed .date {{ color: #1db95499; }}

    .section-label {{
      max-width: 680px;
      margin: 2rem auto 0.75rem;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #444;
    }}
  </style>
</head>
<body>

  <div class="hero">
    <div class="album-title">{ALBUM_DISPLAY}</div>
    <div class="artist-name">{ARTIST_DISPLAY}</div>
    <a class="spotify-btn" href="{SPOTIFY_LINK}" target="_blank" rel="noopener">
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
      </svg>
      Listen on Spotify
    </a>
  </div>

  <div class="progress-section">
    <div class="progress-header">
      <span class="progress-label">Platforms live</span>
      <span class="progress-count">{count} <span>/ {total}</span></span>
    </div>
    <div class="bar-bg"><div class="bar-fill"></div></div>
    <div class="last-checked">Last checked: {last_checked}</div>
  </div>

  <div class="grid">
    {all_cards}
  </div>

</body>
</html>
"""
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard written to {HTML_FILE}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    status = load_status()
    newly_confirmed = []

    print(f"\n🎵 Checking platforms for '{ALBUM_DISPLAY}' by {ARTIST_DISPLAY}\n")

    for name, checker in CHECKABLE.items():
        platform = status["platforms"].get(name, {"status": "pending", "confirmed_at": None, "link": None})

        if platform["status"] == "confirmed":
            print(f"  ✓ {name} (already confirmed)")
            continue

        print(f"  ○ Checking {name}...", end=" ", flush=True)
        try:
            found, link = checker()
        except Exception as e:
            print(f"error ({e})")
            continue

        if found:
            print("✓ FOUND")
            status["platforms"][name] = {
                "status": "confirmed",
                "confirmed_at": datetime.now(timezone.utc).isoformat(),
                "link": link,
            }
            newly_confirmed.append((name, link))
        else:
            print("not yet")

    # Ensure Spotify is always in status
    if "Spotify" not in status["platforms"]:
        status["platforms"]["Spotify"] = {
            "status": "confirmed",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "link": SPOTIFY_LINK,
        }

    # Ensure regional platforms are in status
    for name in REGIONAL:
        if name not in status["platforms"]:
            status["platforms"][name] = {"status": "manual", "confirmed_at": None, "link": None}

    status["last_checked"] = datetime.now(timezone.utc).isoformat()

    confirmed_total = sum(1 for v in status["platforms"].values() if v["status"] == "confirmed")
    total = len(status["platforms"])
    print(f"\n📊 {confirmed_total}/{total} platforms confirmed")

    # Send HA notifications for newly confirmed platforms
    if newly_confirmed:
        print(f"\n🔔 Sending {len(newly_confirmed)} notification(s)...")
        for name, link in newly_confirmed:
            notify_ha(name, link)

    save_status(status)
    generate_html(status)
    print("\nDone.")


if __name__ == "__main__":
    main()
