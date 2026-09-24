import asyncio
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

from pypresence import Presence
from pypresence.types import ActivityType

CLIENT_ID = "put ur discord bot application id"
APP_ID_HINT = "apple"      
POLL_SECONDS = 5           
IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"


@dataclass
class Playing:
    title: str
    subtitle: str = ""           
    position: float = 0.0        
    duration: float = 0.0        
    is_playing: bool = True


async def _win_get_playing(list_only: bool = False) -> Optional[Playing]:
    try:
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Manager,
        )
    except ImportError:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Manager,
        )

    manager = await Manager.request_async()
    sessions = manager.get_sessions()

    if list_only:
        for s in sessions:
            print("Session:", s.source_app_user_model_id)
        return None

    for s in sessions:
        if APP_ID_HINT.lower() not in s.source_app_user_model_id.lower():
            continue
        props = await s.try_get_media_properties_async()
        if not props or not props.title:
            continue

        status = s.get_playback_info().playback_status  
        timeline = s.get_timeline_properties()
        subtitle = props.artist or props.album_title or ""
        return Playing(
            title=props.title,
            subtitle=subtitle,
            position=timeline.position.total_seconds(),
            duration=timeline.end_time.total_seconds(),
            is_playing=(int(status) == 4),
        )
    return None


MAC_SCRIPT = '''
tell application "System Events"
    if not (exists process "TV") then return "NOTRUNNING"
end tell
tell application "TV"
    if player state is stopped then return "STOPPED"
    set st to (player state as string)
    set t to name of current track
    set sh to ""
    set sn to ""
    set en to ""
    try
        set sh to show of current track
        set sn to season number of current track
        set en to episode number of current track
    end try
    set d to duration of current track
    set p to player position
    return st & "|||" & t & "|||" & sh & "|||" & sn & "|||" & en & "|||" & d & "|||" & p
end tell
'''


def _mac_get_playing() -> Optional[Playing]:
    out = subprocess.run(
        ["osascript", "-e", MAC_SCRIPT], capture_output=True, text=True
    ).stdout.strip()
    if not out or out in ("NOTRUNNING", "STOPPED"):
        return None

    state, title, show, season, episode, dur, pos = (out.split("|||") + [""] * 7)[:7]
    subtitle = ""
    if show and show != "missing value":
        subtitle = show
        if season not in ("", "0", "missing value") and episode not in ("", "0", "missing value"):
            subtitle += f" · S{season} E{episode}"
    try:
        return Playing(
            title=title,
            subtitle=subtitle,
            position=float(pos or 0),
            duration=float(dur or 0),
            is_playing=(state == "playing"),
        )
    except ValueError:
        return None


GENERIC_TITLE = "In the Apple TV app"
_art_cache: dict = {}


def _itunes_search(term: str, media: str, entity: str) -> Optional[str]:
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": term, "media": media, "entity": entity, "limit": 5}
    )
    with urllib.request.urlopen(url, timeout=6) as r:
        results = json.load(r).get("results", [])
    term_l = term.lower()
    for item in results:
        name = (item.get("collectionName") or item.get("trackName") or "").lower()
        show = (item.get("artistName") or "").lower()
        if term_l in name or term_l in show:
            art = item.get("artworkUrl100")
            if art:
                return art.replace("100x100bb", "600x600bb")
    return None


def _tvmaze_search(term: str) -> Optional[str]:
    url = "https://api.tvmaze.com/search/shows?" + urllib.parse.urlencode({"q": term})
    with urllib.request.urlopen(url, timeout=6) as r:
        results = json.load(r)
    term_l = term.lower()
    partial = None
    for r in results:
        show = r.get("show", {})
        img = show.get("image") or {}
        art = img.get("original") or img.get("medium")
        if not art:
            continue
        art = art.replace("http://", "https://")
        name = (show.get("name") or "").lower()
        if name == term_l:
            return art
        if partial is None and term_l in name:
            partial = art
    return partial


def get_artwork(*terms: str) -> Optional[str]:
    """Find a poster URL for a title (TV season first, then movie)."""
    for term in terms:
        term = (term or "").strip()
        if not term or term == GENERIC_TITLE:
            continue
        if term in _art_cache:
            if _art_cache[term]:
                return _art_cache[term]
            continue
        found = None
        try:
            found = (
                _tvmaze_search(term)
                or _itunes_search(term, "tvShow", "tvSeason")
                or _itunes_search(term, "movie", "movie")
            )
        except Exception as e:
            print(f"(poster lookup failed for '{term}': {e})")
        print(f"Poster for '{term}': {found or 'not found'}")
        _art_cache[term] = found
        if found:
            return found
    return None


def _win_fallback(manual_title: Optional[str]) -> Optional[Playing]:
    """If Windows exposes no media session, use the Apple TV window title,
    or a title typed by the user, or just show that the app is open."""
    ps = (
        "$p = Get-Process AppleTV -ErrorAction SilentlyContinue; "
        "if ($p) { 'RUNNING|' + (($p | ForEach-Object { $_.MainWindowTitle }) -join ';') }"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:
        return None
    if not out.startswith("RUNNING"):
        return None

    window_title = out.split("|", 1)[1].strip(" ;") if "|" in out else ""
    if window_title.lower() in ("", "apple tv"):
        window_title = ""
    title = manual_title or window_title or GENERIC_TITLE
    return Playing(title=title, is_playing=True)


def get_playing(manual_title: Optional[str]) -> Optional[Playing]:
    if IS_WINDOWS:
        p = asyncio.run(_win_get_playing())
        if p:
            if manual_title:
                p.title = manual_title
            return p
        return _win_fallback(manual_title)
    if IS_MAC:
        return _mac_get_playing()
    raise SystemExit("Apple TV desktop app is only available on Windows and macOS.")


def main():
    if "--list" in sys.argv and IS_WINDOWS:
        asyncio.run(_win_get_playing(list_only=True))
        return

    if "--test-art" in sys.argv:
        i = sys.argv.index("--test-art")
        term = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        print(get_artwork(term) or "No poster found")
        return

   
    manual_title = None
    if "--title" in sys.argv:
        i = sys.argv.index("--title")
        if i + 1 < len(sys.argv):
            manual_title = sys.argv[i + 1]

    rpc = Presence(CLIENT_ID)
    rpc.connect()
    print("Connected to Discord. Watching for Apple TV... (Ctrl+C to stop)")

    last_key = None
    session_start = None
    idle_polls = 0
    try:
        while True:
            p = get_playing(manual_title)

            if p is None or not p.is_playing:
                idle_polls += 1
                if last_key is not None:
                    rpc.clear()
                    last_key = None
                    session_start = None
                    print("Apple TV not playing/open - presence cleared.")
                elif idle_polls % 6 == 1:  
                    print("Waiting: Apple TV app not detected (is it open?)")
            else:
                idle_polls = 0
                now = int(time.time())
                has_progress = p.duration > 0

                if has_progress:
                    start = now - int(p.position)
                    end = start + int(p.duration)
                    key = (p.title, p.subtitle, start // 10)
                else:
                    
                    if last_key is None or last_key[0] != p.title:
                        session_start = now
                    start, end = session_start, None
                    key = (p.title, p.subtitle, 0)

                if key != last_key:
                    kwargs = dict(
                        activity_type=ActivityType.WATCHING,
                        details=p.title[:128],
                        state=(p.subtitle or "Apple TV")[:128],
                        start=start,
                    )
                    if end:
                        kwargs["end"] = end
                    poster = get_artwork(p.title, p.subtitle.split("\u00b7")[0])
                    if poster:
                        kwargs["large_image"] = poster
                        kwargs["large_text"] = p.title[:128]
                    rpc.update(**kwargs)
                    last_key = key
                    print(f"Presence set: {p.title} {('- ' + p.subtitle) if p.subtitle else ''}")

            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        rpc.clear()
        rpc.close()


if __name__ == "__main__":
    main()
