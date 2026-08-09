import { useState } from "react";
import UploadPanel from "./components/UploadPanel.jsx";
import ImportPanel from "./components/ImportPanel.jsx";
import TrackTable from "./components/TrackTable.jsx";
import SortControls from "./components/SortControls.jsx";
import ExportButtons from "./components/ExportButtons.jsx";
import { sortTracks } from "./api.js";

// When a Serato-imported track (no BPM/key, needs_analysis=true) is later
// matched by filename to a freshly analyzed upload, replace it in place
// (keeping its id) instead of creating a duplicate row.
function mergeTracks(prevPool, newTracks) {
  const pool = [...prevPool];
  for (const incoming of newTracks) {
    const matchIndex = pool.findIndex(
      (t) => t.needs_analysis && t.filename.toLowerCase() === incoming.filename.toLowerCase()
    );
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
  return pool;
}

export default function App() {
  const [pool, setPool] = useState([]);
  const [sortedResult, setSortedResult] = useState(null);
  const [isSorting, setIsSorting] = useState(false);
  const [sortError, setSortError] = useState(null);

  function handleTracksAdded(newTracks) {
    setPool((prev) => mergeTracks(prev, newTracks));
    setSortedResult(null);
  }

  function handleRemove(id) {
    setPool((prev) => prev.filter((t) => t.id !== id));
    setSortedResult(null);
  }

  async function handleSort() {
    if (pool.length < 2) return;
    setIsSorting(true);
    setSortError(null);
    try {
      const result = await sortTracks(pool);
      setSortedResult(result);
    } catch (err) {
      setSortError(err.message);
    } finally {
      setIsSorting(false);
    }
  }

  const needsAnalysisCount = pool.filter((t) => t.needs_analysis).length;

  return (
    <div className="app">
      <header>
        <h1>DJ Track Sorter</h1>
        <p>Auto-sort your set by musical key (Camelot) and BPM compatibility.</p>
      </header>

      <main>
        <UploadPanel onTracksUploaded={handleTracksAdded} />
        <ImportPanel onTracksImported={handleTracksAdded} />

        {pool.length > 0 && (
          <div className="panel">
            <h2>Track pool ({pool.length})</h2>
            {needsAnalysisCount > 0 && (
              <p className="hint">
                {needsAnalysisCount} track{needsAnalysisCount === 1 ? "" : "s"} still need
                their audio uploaded above for BPM/key analysis before sorting can place
                them well.
              </p>
            )}
            <TrackTable tracks={pool} onRemove={handleRemove} />
          </div>
        )}

        {pool.length > 0 && (
          <div className="panel">
            <h2>Sort</h2>
            <SortControls onSort={handleSort} disabled={pool.length < 2} isSorting={isSorting} />
            {sortError && <p className="error">{sortError}</p>}
          </div>
        )}

        {sortedResult && (
          <div className="panel">
            <h2>Sorted playlist</h2>
            <TrackTable tracks={sortedResult.tracks} transitions={sortedResult.transitions} />
            <ExportButtons tracks={sortedResult.tracks} playlistName="DJ Track Sorter Playlist" />
          </div>
        )}
      </main>
    </div>
  );
}
