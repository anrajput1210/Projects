import { useState } from "react";
import { FileCode, ListMusic, Info, X } from "lucide-react";
import { exportRekordboxXml, exportM3u } from "../lib/api.js";

export default function ExportBar({ tracks, playlistName, onToast }) {
  const [isExporting, setIsExporting] = useState(false);
  const [noteDismissed, setNoteDismissed] = useState(false);

  async function handleExport(exportFn, label) {
    setIsExporting(true);
    try {
      await exportFn(tracks, playlistName);
      onToast(`${label} exported`, "success");
    } catch (err) {
      onToast(err.message, "error");
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={isExporting}
          onClick={() => handleExport(exportRekordboxXml, "Rekordbox XML")}
          className="flex items-center gap-1.5 rounded-sm bg-led px-4 py-2 text-small font-semibold text-[#111111] transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          <FileCode size={15} /> Export Rekordbox XML
        </button>
        <button
          type="button"
          disabled={isExporting}
          onClick={() => handleExport(exportM3u, "M3U")}
          className="flex items-center gap-1.5 rounded-sm border border-chassis px-4 py-2 text-small font-semibold text-ink transition-colors hover:border-led disabled:opacity-50"
        >
          <ListMusic size={15} /> Export M3U
        </button>
      </div>

      {!noteDismissed && (
        <p className="mt-4 flex items-start gap-2 rounded-md border border-chassis bg-panel p-3 text-small text-ink/60">
          <Info size={15} className="mt-0.5 shrink-0" />
          <span className="flex-1">
            Freshly-uploaded tracks export with just a filename — Rekordbox will show them as
            missing until you relink them.
          </span>
          <button
            type="button"
            onClick={() => setNoteDismissed(true)}
            aria-label="Dismiss note"
            className="shrink-0 text-ink/40 hover:text-ink"
          >
            <X size={14} />
          </button>
        </p>
      )}
    </div>
  );
}
