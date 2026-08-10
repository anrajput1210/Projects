import { useMemo, useRef, useState } from "react";
import { ArrowRight, Disc3 } from "lucide-react";
import TrackRow from "../components/TrackRow/TrackRow.jsx";
import { uploadTracks } from "../lib/api.js";

export default function LibraryScreen({ pool, audioUrls, onRemove, onAddTracks, onNavigateSort, onToast }) {
  const [keyFilter, setKeyFilter] = useState("all");
  const [bpmMin, setBpmMin] = useState("");
  const [bpmMax, setBpmMax] = useState("");
  const [playingId, setPlayingId] = useState(null);
  const audioRef = useRef(null);

  const availableKeys = useMemo(() => {
    const set = new Set(pool.map((t) => t.camelot_key).filter(Boolean));
    return Array.from(set).sort();
  }, [pool]);

  const filtered = useMemo(() => {
    return pool.filter((t) => {
      if (keyFilter !== "all" && t.camelot_key !== keyFilter) return false;
      if (bpmMin && (!t.bpm || t.bpm < Number(bpmMin))) return false;
      if (bpmMax && (!t.bpm || t.bpm > Number(bpmMax))) return false;
      return true;
    });
  }, [pool, keyFilter, bpmMin, bpmMax]);

  function togglePlay(id) {
    const url = audioUrls.get(id);
    if (!url) return;
    if (playingId === id) {
      audioRef.current?.pause();
      setPlayingId(null);
      return;
    }
    if (audioRef.current) {
      audioRef.current.src = url;
      audioRef.current.play();
    }
    setPlayingId(id);
  }

  async function handleUploadAudio(track, file) {
    try {
      const tracks = await uploadTracks([file]);
      onAddTracks(tracks, [file]);
      onToast(`${track.title || track.filename} analyzed`, "success");
    } catch (err) {
      onToast(err.message, "error");
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <audio ref={audioRef} onEnded={() => setPlayingId(null)} className="hidden" />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-h1 font-semibold">Library ({pool.length} tracks)</h1>

        {pool.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={keyFilter}
              onChange={(e) => setKeyFilter(e.target.value)}
              aria-label="Filter by key"
              className="rounded-sm border border-chassis bg-panel px-2.5 py-1.5 text-small"
            >
              <option value="all">All keys</option>
              {availableKeys.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
            <input
              type="number"
              inputMode="numeric"
              placeholder="BPM min"
              value={bpmMin}
              onChange={(e) => setBpmMin(e.target.value)}
              aria-label="Minimum BPM"
              className="w-24 rounded-sm border border-chassis bg-panel px-2.5 py-1.5 text-small"
            />
            <input
              type="number"
              inputMode="numeric"
              placeholder="BPM max"
              value={bpmMax}
              onChange={(e) => setBpmMax(e.target.value)}
              aria-label="Maximum BPM"
              className="w-24 rounded-sm border border-chassis bg-panel px-2.5 py-1.5 text-small"
            />
          </div>
        )}
      </div>

      {pool.length === 0 ? (
        <div className="mt-10 flex flex-col items-center gap-3 rounded-md border border-chassis bg-panel py-16 text-center">
          <Disc3 size={28} className="text-chassis" />
          <p className="font-display text-eyebrow uppercase text-ink/50">Empty library</p>
          <p className="max-w-sm text-small text-ink/50">
            Import tracks to see them on the wheel and get sorting.
          </p>
        </div>
      ) : (
        <>
          <div className="mt-6 overflow-hidden rounded-md border border-chassis bg-panel">
            {filtered.map((track) => (
              <TrackRow
                key={track.id}
                track={track}
                isPlaying={playingId === track.id}
                hasAudio={audioUrls.has(track.id)}
                onTogglePlay={togglePlay}
                onRemove={onRemove}
                onUploadAudio={handleUploadAudio}
              />
            ))}
            {filtered.length === 0 && (
              <p className="p-6 text-center text-small text-ink/50">No tracks match this filter.</p>
            )}
          </div>

          <button
            type="button"
            onClick={onNavigateSort}
            disabled={pool.length < 2}
            className="mt-6 inline-flex items-center gap-1.5 rounded-sm bg-led px-4 py-2 text-small font-semibold text-[#111111] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Sort playlist <ArrowRight size={15} />
          </button>
          {pool.length < 2 && (
            <p className="mt-2 text-small text-ink/50">Add at least 2 tracks to sort.</p>
          )}
        </>
      )}
    </div>
  );
}
