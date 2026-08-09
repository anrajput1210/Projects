"""Parse a Rekordbox XML library export.

Rekordbox XML (Library > Export Collection in XML format) already contains
BPM (`AverageBpm`) and key (`Tonality`) for any track Rekordbox has
analyzed — we use that directly instead of re-analyzing audio we don't even
have access to (the XML only references file paths on the DJ's machine).
"""
from typing import List
from urllib.parse import unquote, urlparse
from uuid import uuid4
from xml.etree import ElementTree as ET

from app.camelot import parse_key_string
from app.models import Track


def parse_rekordbox_xml(xml_bytes: bytes) -> List[Track]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"Couldn't parse this as XML: {exc}") from exc

    collection = root.find(".//COLLECTION")
    if collection is None:
        raise ValueError("This doesn't look like a Rekordbox XML export (no <COLLECTION> found).")

    tracks: List[Track] = []
    for node in collection.findall("TRACK"):
        name = node.get("Name") or "Unknown"
        artist = node.get("Artist") or None

        bpm_raw = node.get("AverageBpm")
        bpm = float(bpm_raw) if bpm_raw else None

        tonality = node.get("Tonality")
        camelot = parse_key_string(tonality) if tonality else None

        location = node.get("Location")
        if location:
            filename = unquote(urlparse(location).path).split("/")[-1]
        else:
            filename = name

        total_time = node.get("TotalTime")
        duration_sec = float(total_time) if total_time else None

        tracks.append(
            Track(
                id=str(uuid4()),
                filename=filename or name,
                title=name,
                artist=artist,
                bpm=bpm,
                camelot_key=camelot,
                key_name=tonality,
                duration_sec=duration_sec,
                source="rekordbox",
                needs_analysis=(bpm is None or camelot is None),
                original_location=location,
            )
        )

    if not tracks:
        raise ValueError("No <TRACK> entries found in this Rekordbox XML export.")

    return tracks
