"""Build an M3U (extended) playlist file from a sorted track list."""
from typing import List

from app.models import Track


def build_m3u(tracks: List[Track]) -> str:
    lines = ["#EXTM3U"]
    for track in tracks:
        duration = int(track.duration_sec) if track.duration_sec else -1
        title = f"{track.artist} - {track.title}" if track.artist and track.title else (track.title or track.filename)
        lines.append(f"#EXTINF:{duration},{title}")
        lines.append(track.filename)
    return "\n".join(lines) + "\n"
