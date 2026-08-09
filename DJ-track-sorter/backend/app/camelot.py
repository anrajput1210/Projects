"""Camelot Wheel conversion and key-string parsing.

The Camelot Wheel is the de-facto DJ notation for harmonic mixing: 12
numbers (1-12) around the circle of fifths, each with an A (minor) and B
(major) letter. Keys that are numerically adjacent, or share a number with
a different letter (relative major/minor), mix well together.
"""
import re
from typing import Optional

PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Pitch class (0=C .. 11=B) -> Camelot number, for each mode.
_MAJOR_CAMELOT_NUMBER = {0: 8, 1: 3, 2: 10, 3: 5, 4: 12, 5: 7, 6: 2, 7: 9, 8: 4, 9: 11, 10: 6, 11: 1}
_MINOR_CAMELOT_NUMBER = {0: 5, 1: 12, 2: 7, 3: 2, 4: 9, 5: 4, 6: 11, 7: 6, 8: 1, 9: 8, 10: 3, 11: 10}

_NOTE_TO_PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def key_to_camelot(pitch_class: int, mode: str) -> str:
    """pitch_class: 0-11 (C=0). mode: 'major' or 'minor'."""
    pitch_class = pitch_class % 12
    if mode == "major":
        return f"{_MAJOR_CAMELOT_NUMBER[pitch_class]}B"
    return f"{_MINOR_CAMELOT_NUMBER[pitch_class]}A"


def key_name(pitch_class: int, mode: str) -> str:
    label = "minor" if mode == "minor" else "major"
    return f"{PITCH_CLASSES[pitch_class % 12]} {label}"


def parse_key_string(raw: Optional[str]) -> Optional[str]:
    """Best-effort conversion of a free-form key string to Camelot notation.

    Handles: already-Camelot codes ("8A"), note names with optional
    accidental and minor suffix ("F#m", "Ab", "C#min", "Bb Major"), and
    common DJ-software variants. Returns None if it can't be parsed.
    """
    if not raw:
        return None
    raw = raw.strip()

    camelot_match = re.match(r"^(1[0-2]|[1-9])\s*([AaBb])$", raw)
    if camelot_match:
        return f"{camelot_match.group(1)}{camelot_match.group(2).upper()}"

    note_match = re.match(
        r"^([A-Ga-g])\s*([#♯b♭]?)\s*(maj(?:or)?|min(?:or)?|m)?$", raw
    )
    if not note_match:
        return None

    letter, accidental, mode_token = note_match.groups()
    pitch_class = _NOTE_TO_PITCH_CLASS[letter.upper()]
    if accidental in ("#", "♯"):
        pitch_class = (pitch_class + 1) % 12
    elif accidental in ("b", "♭"):
        pitch_class = (pitch_class - 1) % 12

    mode_token = (mode_token or "").lower()
    mode = "minor" if mode_token.startswith("min") or mode_token == "m" else "major"

    return key_to_camelot(pitch_class, mode)


def camelot_compatibility(code_a: Optional[str], code_b: Optional[str]) -> float:
    """0-1 score for how well two Camelot codes mix.

    1.0  same key
    0.9  relative major/minor (same number, different letter)
    0.8  adjacent number, same letter (a "wheel move")
    0.5  adjacent number, different letter (riskier, but doable)
    0.1  anything else (baseline so the sorter can still produce *an* order)
    0.0  missing data on either side
    """
    if not code_a or not code_b:
        return 0.0

    match_a = re.match(r"^(\d{1,2})([AB])$", code_a)
    match_b = re.match(r"^(\d{1,2})([AB])$", code_b)
    if not match_a or not match_b:
        return 0.0

    num_a, letter_a = int(match_a.group(1)), match_a.group(2)
    num_b, letter_b = int(match_b.group(1)), match_b.group(2)

    if num_a == num_b and letter_a == letter_b:
        return 1.0
    if num_a == num_b:
        return 0.9

    diff = min((num_a - num_b) % 12, (num_b - num_a) % 12)
    if diff == 1 and letter_a == letter_b:
        return 0.8
    if diff == 1:
        return 0.5
    return 0.1
