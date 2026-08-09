"""BPM and musical-key detection using librosa only.

We deliberately skip essentia: it has poor/no prebuilt wheels on Windows and
on the free-tier Linux containers this project targets (Render/Railway),
which would turn "pip install" into a multi-hour source build or an outright
failure. librosa covers both BPM (`beat_track`) and key (chroma features +
the classic Krumhansl-Schmuckler profile-correlation method) with pure
NumPy/SciPy, so the whole stack stays `pip install`-able for free.
"""
import os
import shutil
import tempfile
from typing import BinaryIO, Optional

import librosa
import numpy as np

from app.camelot import key_name, key_to_camelot

# BPM and key stay effectively constant through the vast majority of DJ-
# friendly tracks (that's what makes them DJ-friendly), so decoding and
# analyzing the first minute is enough — and it's the single biggest lever
# on upload speed, since MP3 decode cost scales with how much audio we ask
# librosa to read. A 6-minute track goes from decoding 360s to 60s, a ~6x
# cut. The track's *reported* duration is still the true full length (see
# below), only the analysis window is capped.
ANALYSIS_DURATION_SEC = 60

# Krumhansl-Schmuckler key profiles: the perceived "fit" of each pitch class
# within a major/minor tonal context, from cognition-of-music research. We
# correlate a track's average chroma vector against all 24 rotations of
# these two profiles and take the best match.
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def detect_key(y: np.ndarray, sr: int) -> tuple[int, str, float]:
    """Returns (pitch_class 0-11, mode 'major'|'minor', confidence 0-1)."""
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)

    best_score = -np.inf
    best_pitch_class = 0
    best_mode = "major"

    for pitch_class in range(12):
        major_score = np.corrcoef(chroma_mean, np.roll(_MAJOR_PROFILE, pitch_class))[0, 1]
        minor_score = np.corrcoef(chroma_mean, np.roll(_MINOR_PROFILE, pitch_class))[0, 1]

        if major_score > best_score:
            best_score, best_pitch_class, best_mode = major_score, pitch_class, "major"
        if minor_score > best_score:
            best_score, best_pitch_class, best_mode = minor_score, pitch_class, "minor"

    # Correlation is in [-1, 1]; clamp/rescale to a friendlier 0-1 confidence.
    confidence = float(np.clip((best_score + 1) / 2, 0.0, 1.0))
    return best_pitch_class, best_mode, confidence


def analyze_audio(file_obj: BinaryIO, filename: str) -> dict:
    """Run BPM + key detection on an audio file-like object.

    librosa's MP3 decoding (via audioread/ffmpeg) needs a real file path
    rather than an in-memory buffer, so we spool the upload to a temp file,
    analyze it, and delete it immediately afterward — it never persists
    beyond this function call.
    """
    suffix = os.path.splitext(filename)[1].lower() or ".audio"
    tmp_path: Optional[str] = None

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            file_obj.seek(0)
            shutil.copyfileobj(file_obj, tmp)

        # Cheap: reads the file's header/metadata rather than decoding the
        # whole thing, so this stays fast even though we only *analyze* a
        # truncated clip below.
        try:
            duration_sec = float(librosa.get_duration(path=tmp_path))
        except Exception:
            duration_sec = None

        y, sr = librosa.load(tmp_path, sr=22050, mono=True, duration=ANALYSIS_DURATION_SEC)

        if y.size == 0:
            raise ValueError("Decoded audio is empty — the file may be corrupt or silent.")

        if duration_sec is None:
            duration_sec = float(len(y) / sr)

        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(np.round(np.atleast_1d(tempo)[0], 1))

        pitch_class, mode, confidence = detect_key(y, sr)
        camelot = key_to_camelot(pitch_class, mode)

        return {
            "bpm": bpm,
            "camelot_key": camelot,
            "key_name": key_name(pitch_class, mode),
            "key_confidence": round(confidence, 2),
            "duration_sec": round(duration_sec, 1),
        }
    finally:
        if tmp_path is not None:
            os.unlink(tmp_path)
