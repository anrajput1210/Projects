from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Track(BaseModel):
    id: str
    filename: str
    title: Optional[str] = None
    artist: Optional[str] = None

    bpm: Optional[float] = None
    camelot_key: Optional[str] = None  # e.g. "8A"
    key_name: Optional[str] = None  # e.g. "A minor"
    key_confidence: Optional[float] = None  # 0-1, only set for analyzed tracks
    duration_sec: Optional[float] = None

    source: Literal["analyzed", "rekordbox", "serato"] = "analyzed"
    # True when BPM/key are still missing (e.g. a Serato crate entry whose
    # audio hasn't been uploaded yet) and the track needs analysis to be
    # usable by the sorter.
    needs_analysis: bool = False

    # Only set for Rekordbox imports, so re-export can point at the DJ's
    # real file path instead of a synthetic one.
    original_location: Optional[str] = None


class UploadResponse(BaseModel):
    tracks: List[Track]


class ImportResponse(BaseModel):
    tracks: List[Track]


class TransitionScore(BaseModel):
    from_id: str
    to_id: str
    score: float
    key_score: float
    bpm_score: float


class SortRequest(BaseModel):
    tracks: List[Track]


class SortResponse(BaseModel):
    tracks: List[Track]
    transitions: List[TransitionScore]


class ExportRequest(BaseModel):
    tracks: List[Track]
    playlist_name: str = Field(default="DJ Track Sorter Playlist")
