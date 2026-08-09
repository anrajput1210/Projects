"""Parse a Serato .crate file.

Serato's crate format is a flat sequence of tagged chunks (4-byte ASCII tag
+ 4-byte big-endian length + value, UTF-16BE for text fields). A crate is
essentially just an ordered list of track paths — Serato's own BPM/key
analysis lives in the *audio file's* ID3 tags (or Serato's separate
database), not in the crate itself, so imported tracks are flagged
`needs_analysis=True` and the DJ can drop the matching audio files in
afterward to fill in BPM/key.
"""
import struct
from typing import List, Optional
from uuid import uuid4

from app.models import Track

_HEADER_SIZE = 8  # 4-byte tag + 4-byte big-endian length


def _iter_chunks(data: bytes):
    pos = 0
    n = len(data)
    while pos + _HEADER_SIZE <= n:
        tag = data[pos : pos + 4].decode("ascii", errors="replace")
        length = struct.unpack(">I", data[pos + 4 : pos + 8])[0]
        value = data[pos + 8 : pos + 8 + length]
        yield tag, value
        pos += _HEADER_SIZE + length


def _extract_track_path(otrk_value: bytes) -> Optional[str]:
    for tag, value in _iter_chunks(otrk_value):
        if tag == "ptrk":
            try:
                return value.decode("utf-16-be").strip("\x00")
            except UnicodeDecodeError:
                return value.decode("utf-8", errors="ignore").strip("\x00")
    return None


def parse_serato_crate(data: bytes) -> List[Track]:
    tracks: List[Track] = []

    for tag, value in _iter_chunks(data):
        if tag != "otrk":
            continue
        path = _extract_track_path(value)
        if not path:
            continue
        filename = path.replace("\\", "/").split("/")[-1]
        tracks.append(
            Track(
                id=str(uuid4()),
                filename=filename,
                title=None,
                artist=None,
                bpm=None,
                camelot_key=None,
                key_name=None,
                duration_sec=None,
                source="serato",
                needs_analysis=True,
            )
        )

    if not tracks:
        raise ValueError(
            "No tracks found in this .crate file. Serato crates only store "
            "track order, not BPM/key — re-upload the matching audio files "
            "to have them analyzed."
        )

    return tracks
