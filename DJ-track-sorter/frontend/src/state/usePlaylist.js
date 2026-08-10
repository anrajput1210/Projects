import { useCallback, useMemo, useState } from "react";
import { sortTracks as apiSortTracks } from "../lib/api.js";

// The playlist "lives only in React state" per DESIGN.md §7 — one hook,
// no persistence, no external state library. A refresh genuinely loses it.
export function usePlaylist() {
  const [pool, setPool] = useState([]);
  const [order, setOrder] = useState(null); // array of track ids, post-sort
  const [transitions, setTransitions] = useState([]);
  const [isSorting, setIsSorting] = useState(false);
  const [sortError, setSortError] = useState(null);
  // id -> object URL, only populated for tracks whose original File is still
  // held in this tab (fresh uploads) — powers the row play-preview toggle.
  const [audioUrls, setAudioUrls] = useState(new Map());

  const addTracks = useCallback((newTracks, files) => {
    setPool((prev) => {
      const pool = [...prev];
      const urlUpdates = new Map();
      for (const incoming of newTracks) {
        const matchIndex = pool.findIndex(
          (t) => t.needs_analysis && t.filename.toLowerCase() === incoming.filename.toLowerCase()
        );
        const finalId = matchIndex !== -1 ? pool[matchIndex].id : incoming.id;
        if (files) {
          const file = files.find((f) => f.name === incoming.filename);
          if (file) urlUpdates.set(finalId, URL.createObjectURL(file));
        }
        if (matchIndex !== -1) {
          const existing = pool[matchIndex];
          pool[matchIndex] = {
            ...incoming,
            id: existing.id,
            title: existing.title || incoming.title,
            artist: existing.artist || incoming.artist,
          };
        } else {
          pool.push(incoming);
        }
      }
      if (urlUpdates.size) {
        setAudioUrls((prevUrls) => {
          const next = new Map(prevUrls);
          for (const [id, url] of urlUpdates) next.set(id, url);
          return next;
        });
      }
      return pool;
    });
    setOrder(null);
    setTransitions([]);
  }, []);

  const removeTrack = useCallback((id) => {
    setPool((prev) => prev.filter((t) => t.id !== id));
    setOrder((prev) => (prev ? prev.filter((tid) => tid !== id) : prev));
    setAudioUrls((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Map(prev);
      const url = next.get(id);
      if (url) URL.revokeObjectURL(url);
      next.delete(id);
      return next;
    });
  }, []);

  const runSort = useCallback(async () => {
    if (pool.length < 2) return;
    setIsSorting(true);
    setSortError(null);
    try {
      const result = await apiSortTracks(pool);
      setOrder(result.tracks.map((t) => t.id));
      setTransitions(result.transitions || []);
    } catch (err) {
      setSortError(err.message);
    } finally {
      setIsSorting(false);
    }
  }, [pool]);

  const reorder = useCallback((fromIndex, toIndex) => {
    setOrder((prev) => {
      if (!prev) return prev;
      const next = [...prev];
      const [moved] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, moved);
      return next;
    });
  }, []);

  const byId = useMemo(() => new Map(pool.map((t) => [t.id, t])), [pool]);

  const sortedTracks = useMemo(() => {
    if (!order) return null;
    return order.map((id) => byId.get(id)).filter(Boolean);
  }, [order, byId]);

  const transitionByFromId = useMemo(
    () => new Map(transitions.map((t) => [t.from_id, t])),
    [transitions]
  );

  const needsAnalysisCount = useMemo(
    () => pool.filter((t) => t.needs_analysis).length,
    [pool]
  );

  return {
    pool,
    sortedTracks,
    transitions,
    transitionByFromId,
    isSorting,
    sortError,
    needsAnalysisCount,
    hasSorted: Boolean(order),
    audioUrls,
    addTracks,
    removeTrack,
    runSort,
    reorder,
  };
}
