"""Compatibility graph + track ordering.

Tracks are nodes; an edge weight is how well two tracks mix, combining
Camelot key compatibility and BPM closeness — a DJ picking the next track
weighs both together, so there's a single sort that walks that graph
greedily (nearest-neighbor heuristic) to build a playable order, rather than
offering separate "by key only" / "by BPM only" modes.
"""
from typing import List, Optional

from app.camelot import camelot_compatibility
from app.models import Track, TransitionScore

BPM_TOLERANCE = 0.06  # ~6%, per the project's mixing-tolerance requirement


def bpm_compatibility(bpm_a: Optional[float], bpm_b: Optional[float]) -> float:
    """0-1 score for how mixable two BPMs are, within tolerance.

    Also credits half-time/double-time matches (e.g. 174 vs 87), a common
    real-world DJ move for mixing across genres like DnB into house.
    """
    if not bpm_a or not bpm_b:
        return 0.0

    def _closeness(a: float, b: float) -> float:
        diff = abs(a - b) / min(a, b)
        if diff > BPM_TOLERANCE:
            return 0.0
        return 1.0 - (diff / BPM_TOLERANCE)

    direct = _closeness(bpm_a, bpm_b)
    half_double = max(_closeness(bpm_a, bpm_b * 2), _closeness(bpm_a, bpm_b / 2))

    return max(direct, 0.7 * half_double)


def compatibility_score(a: Track, b: Track) -> float:
    key_score = camelot_compatibility(a.camelot_key, b.camelot_key)
    bpm_score = bpm_compatibility(a.bpm, b.bpm)
    return 0.6 * key_score + 0.4 * bpm_score


def _transitions(order: List[Track]) -> List[TransitionScore]:
    transitions = []
    for a, b in zip(order, order[1:]):
        transitions.append(
            TransitionScore(
                from_id=a.id,
                to_id=b.id,
                score=round(compatibility_score(a, b), 2),
                key_score=round(camelot_compatibility(a.camelot_key, b.camelot_key), 2),
                bpm_score=round(bpm_compatibility(a.bpm, b.bpm), 2),
            )
        )
    return transitions


def sort_tracks(tracks: List[Track]) -> tuple[List[Track], List[TransitionScore]]:
    """Nearest-neighbor greedy walk over the compatibility graph.

    Starts from the lowest-BPM track (a sensible opener) and repeatedly
    picks whichever remaining track mixes best with the current end of the
    set, weighing key compatibility and BPM closeness together — the same
    two things a DJ actually looks at when picking the next track. This is
    a heuristic, not an optimal TSP solve — it's O(n^2), which is fine for
    realistic playlist sizes and gives a genuinely playable order rather
    than just grouping identical keys together or ignoring key entirely.
    """
    if not tracks:
        return [], []

    remaining = list(tracks)
    start = min(remaining, key=lambda t: t.bpm if t.bpm is not None else float("inf"))
    order = [start]
    remaining.remove(start)

    while remaining:
        current = order[-1]
        best = max(remaining, key=lambda t: compatibility_score(current, t))
        order.append(best)
        remaining.remove(best)

    return order, _transitions(order)
