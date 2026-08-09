import { useState } from "react";
import { exportM3u, exportRekordboxXml } from "../api.js";

export default function ExportButtons({ tracks, playlistName }) {
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState(null);

  async function handleExport(exportFn) {
    setIsExporting(true);
    setError(null);
    try {
      await exportFn(tracks, playlistName);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="export-buttons">
      <button type="button" disabled={isExporting} onClick={() => handleExport(exportRekordboxXml)}>
        Export Rekordbox XML
      </button>
      <button type="button" disabled={isExporting} onClick={() => handleExport(exportM3u)}>
        Export M3U
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
