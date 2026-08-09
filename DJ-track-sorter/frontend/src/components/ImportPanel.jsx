import { useRef, useState } from "react";
import { importRekordboxXml, importSeratoCrate } from "../api.js";

export default function ImportPanel({ onTracksImported }) {
  const xmlInputRef = useRef(null);
  const crateInputRef = useRef(null);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState(null);

  async function handleImport(importFn, file, inputRef) {
    if (!file) return;

    setIsImporting(true);
    setError(null);

    try {
      const tracks = await importFn(file);
      onTracksImported(tracks);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsImporting(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="panel">
      <h2>Import from DJ software</h2>
      <p className="hint">
        Rekordbox XML exports already carry BPM/key when Rekordbox has analyzed the
        track. Serato crates only store track order — re-upload the matching audio
        files above to get those analyzed.
      </p>
      <div className="import-row">
        <label className="file-label">
          Rekordbox XML export
          <input
            ref={xmlInputRef}
            type="file"
            accept=".xml"
            disabled={isImporting}
            onChange={(e) => handleImport(importRekordboxXml, e.target.files[0], xmlInputRef)}
          />
        </label>
        <label className="file-label">
          Serato crate
          <input
            ref={crateInputRef}
            type="file"
            accept=".crate"
            disabled={isImporting}
            onChange={(e) => handleImport(importSeratoCrate, e.target.files[0], crateInputRef)}
          />
        </label>
      </div>
      {isImporting && <p className="status">Importing…</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
