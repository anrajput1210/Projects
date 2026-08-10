import { useState } from "react";
import { Disc3, RefreshCw } from "lucide-react";
import CamelotDial from "../components/CamelotDial/CamelotDial.jsx";
import SortList from "../components/SortList.jsx";
import ExportBar from "../components/ExportBar.jsx";

export default function SortScreen({
  pool,
  sortedTracks,
  transitionByFromId,
  isSorting,
  sortError,
  hasSorted,
  onSort,
  onReorder,
  onToast,
}) {
  const [activeId, setActiveId] = useState(null);

  const dialTracks = hasSorted ? sortedTracks : pool;
  const order = hasSorted ? sortedTracks.map((t) => t.id) : null;
  const activeIndex = hasSorted ? sortedTracks.findIndex((t) => t.id === activeId) : -1;
  const nowTrack =
    (activeIndex >= 0 && sortedTracks[activeIndex]) || (hasSorted ? sortedTracks[0] : null);
  const nowIndex = hasSorted ? (activeIndex >= 0 ? activeIndex : 0) : -1;

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <p className="text-eyebrow font-display uppercase text-led">Mix path</p>

      <div className="mt-6">
        <CamelotDial
          tracks={dialTracks}
          order={order}
          spinning={isSorting}
          activeId={activeId}
          onHoverTrack={setActiveId}
        />
      </div>

      {hasSorted && nowTrack ? (
        <p className="mt-4 text-center font-data text-data-sm text-ink/70">
          Now: {nowTrack.title || nowTrack.filename} · {nowTrack.camelot_key || "—"} ·{" "}
          {nowTrack.bpm ? Math.round(nowTrack.bpm) : "—"} BPM · step {nowIndex + 1}/
          {sortedTracks.length}
        </p>
      ) : (
        <p className="mt-4 text-center text-small text-ink/50">
          {pool.length < 2 ? "Add at least 2 tracks to sort." : "Ready to sort your set."}
        </p>
      )}

      <p className="mx-auto mt-2 max-w-md text-center text-data-sm text-ink/40">
        Nearest-neighbor by key + BPM — not a perfect solve, but built to be genuinely mixable.
      </p>

      <div className="mt-6 flex justify-center">
        <button
          type="button"
          onClick={onSort}
          disabled={pool.length < 2 || isSorting}
          className="flex items-center gap-1.5 rounded-sm bg-led px-5 py-2.5 text-small font-semibold text-[#111111] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isSorting ? (
            <>
              <RefreshCw size={15} className="animate-spin" /> Sorting…
            </>
          ) : (
            <>
              <Disc3 size={15} /> {hasSorted ? "Re-sort playlist" : "Sort playlist"}
            </>
          )}
        </button>
      </div>

      {sortError && <p className="mt-3 text-center text-small text-danger">{sortError}</p>}

      {hasSorted && sortedTracks && (
        <div className="mt-8">
          <h2 className="mb-3 text-h2 font-semibold">Set order</h2>
          <p className="mb-3 text-small text-ink/50">Drag to override, or focus a row and use arrow keys.</p>
          <SortList
            tracks={sortedTracks}
            transitionByFromId={transitionByFromId}
            activeId={activeId}
            onHover={setActiveId}
            onReorder={onReorder}
          />

          <div className="mt-6">
            <ExportBar tracks={sortedTracks} playlistName="CRATEWHEEL Playlist" onToast={onToast} />
          </div>
        </div>
      )}
    </div>
  );
}
