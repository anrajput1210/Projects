"""Build a Rekordbox-importable XML file from a sorted track list.

Note on `Location`: for tracks that came from a fresh upload (not a
Rekordbox import), we don't know the real path on the DJ's filesystem —
only the filename. Rekordbox will show these as "missing" until the DJ
relinks them, which is an inherent limitation of not persisting/storing the
original files (see README). Tracks that came in via Rekordbox XML import
keep their original Location.
"""
from typing import List
from urllib.parse import quote
from xml.etree import ElementTree as ET

from app.models import Track


def build_rekordbox_xml(tracks: List[Track], playlist_name: str = "DJ Track Sorter Playlist") -> bytes:
    root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
    ET.SubElement(root, "PRODUCT", Name="DJ Track Sorter", Version="1.0", Company="DJ Track Sorter")

    collection = ET.SubElement(root, "COLLECTION", Entries=str(len(tracks)))
    track_ids = {}

    for index, track in enumerate(tracks, start=1):
        track_ids[track.id] = index
        attrib = {
            "TrackID": str(index),
            "Name": track.title or track.filename,
            "Artist": track.artist or "",
            "Location": track.original_location or f"file://localhost/{quote(track.filename)}",
        }
        if track.bpm:
            attrib["AverageBpm"] = f"{track.bpm:.2f}"
        if track.key_name:
            attrib["Tonality"] = track.key_name
        elif track.camelot_key:
            attrib["Tonality"] = track.camelot_key
        if track.duration_sec:
            attrib["TotalTime"] = str(int(track.duration_sec))

        ET.SubElement(collection, "TRACK", attrib)

    playlists = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists, "NODE", Type="0", Name="ROOT", Count="1")
    playlist_node = ET.SubElement(
        root_node, "NODE", Type="1", Name=playlist_name, KeyType="0", Entries=str(len(tracks))
    )
    for track in tracks:
        ET.SubElement(playlist_node, "TRACK", Key=str(track_ids[track.id]))

    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)
