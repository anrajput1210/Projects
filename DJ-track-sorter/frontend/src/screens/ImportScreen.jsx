import { useState } from "react";
import { X, ArrowRight, AlertTriangle } from "lucide-react";
import ImportTabs from "../components/ImportTabs/ImportTabs.jsx";
import UploadDeck from "../components/UploadDeck.jsx";
import KeyBadge from "../components/KeyBadge.jsx";
import { uploadTracks, importRekordboxXml, importSeratoCrate } from "../lib/api.js";

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes;
  let unit = -1;
  do {
    value /= 1024;
    unit += 1;
  } while (value >= 1024 && unit < units.length - 1);
  return `${value.toFixed(1)}${units[unit]}`;
}

export default function ImportScreen({ onTracksAdded, onToast }) {
  const [activeTab, setActiveTab] = useState("upload");

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <p className="text-eyebrow font-display uppercase text-led">Start a session</p>
      <h1 className="mt-3 text-h1 font-semibold">Bring in your tracks</h1>

      <div className="mt-6">
        <ImportTabs active={activeTab} onChange={setActiveTab} />
      </div>

      <div className="mt-6">
        {activeTab === "upload" && <UploadTab onTracksAdded={onTracksAdded} onToast={onToast} />}
        {activeTab === "rekordbox" && (
          <ImportPreviewTab
            kind="rekordbox"
            hint="Drop Rekordbox XML — up to 5GB"
            accept=".xml"
            importFn={importRekordboxXml}
            onTracksAdded={onTracksAdded}
            onToast={onToast}
          />
        )}
        {activeTab === "serato" && (
          <ImportPreviewTab
            kind="serato"
            hint="Drop a Serato .crate file"
            accept=".crate"
            importFn={importSeratoCrate}
            onTracksAdded={onTracksAdded}
            onToast={onToast}
          />
        )}
      </div>
    </div>
  );
}

function UploadTab({ onTracksAdded, onToast }) {
  const [queued, setQueued] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  function addFiles(files) {
    setQueued((prev) => [...prev, ...files]);
  }

  function removeFile(index) {
    setQueued((prev) => prev.filter((_, i) => i !== index));
  }

  async function analyze() {
    if (queued.length === 0) return;
    setIsUploading(true);
    setProgress(0);
    setError(null);
    try {
      const tracks = await uploadTracks(queued, setProgress);
      onTracksAdded(tracks, queued);
      onToast(`${tracks.length} track${tracks.length === 1 ? "" : "s"} analyzed`, "success");
      setQueued([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div>
      <UploadDeck
        accept=".mp3,.wav,.flac"
        multiple
        hint="Drop MP3 / WAV / FLAC — up to 5GB"
        onFiles={addFiles}
        disabled={isUploading}
      />

      {queued.length > 0 && (
        <div className="mt-5">
          <ul className="divide-y divide-chassis border-y border-chassis">
            {queued.map((file, i) => (
              <li key={`${file.name}-${i}`} className="flex items-center justify-between py-2.5">
                <span className="truncate text-small">{file.name}</span>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="font-data text-data-sm text-ink/50">{formatBytes(file.size)}</span>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    disabled={isUploading}
                    aria-label={`Remove ${file.name}`}
                    className="text-ink/40 hover:text-danger disabled:opacity-40"
                  >
                    <X size={15} />
                  </button>
                </div>
              </li>
            ))}
          </ul>

          {isUploading && (
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-chassis/40">
              <div
                className="h-full rounded-full bg-led transition-all"
                style={{ width: `${Math.round(progress * 100)}%` }}
              />
            </div>
          )}

          <button
            type="button"
            onClick={analyze}
            disabled={isUploading}
            className="mt-4 inline-flex items-center gap-1.5 rounded-sm bg-led px-4 py-2 text-small font-semibold text-[#111111] transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isUploading ? "Analyzing…" : `Analyze ${queued.length} track${queued.length === 1 ? "" : "s"}`}
            {!isUploading && <ArrowRight size={15} />}
          </button>
        </div>
      )}

      {error && <p className="mt-3 text-small text-danger">{error}</p>}
    </div>
  );
}

function ImportPreviewTab({ kind, hint, accept, importFn, onTracksAdded, onToast }) {
  const [preview, setPreview] = useState(null);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState(null);

  async function handleFile(files) {
    const file = files[0];
    if (!file) return;
    setIsImporting(true);
    setError(null);
    try {
      const tracks = await importFn(file);
      setPreview(tracks);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsImporting(false);
    }
  }

  function commit() {
    if (!preview) return;
    onTracksAdded(preview);
    onToast(`${preview.length} track${preview.length === 1 ? "" : "s"} added to library`, "success");
    setPreview(null);
  }

  return (
    <div>
      <UploadDeck accept={accept} hint={hint} onFiles={handleFile} disabled={isImporting} />
      {isImporting && <p className="mt-3 text-small text-ink/60">Parsing…</p>}
      {error && <p className="mt-3 text-small text-danger">{error}</p>}

      {kind === "serato" && preview && (
        <p className="mt-5 flex items-start gap-2 rounded-md border border-chassis bg-panel p-3 text-small text-ink/70">
          <AlertTriangle size={15} className="mt-0.5 shrink-0 text-danger" />
          Serato crates don't carry BPM or key — re-upload the audio for these to analyze them.
        </p>
      )}

      {preview && preview.length > 0 && (
        <div className="mt-4">
          <div className="overflow-x-auto rounded-md border border-chassis">
            <table className="w-full text-left text-small">
              <thead>
                <tr className="border-b border-chassis text-ink/50">
                  <th className="px-3 py-2 font-medium">Title</th>
                  <th className="px-3 py-2 font-medium">
                    {kind === "rekordbox" ? "Existing BPM" : "BPM"}
                  </th>
                  <th className="px-3 py-2 font-medium">
                    {kind === "rekordbox" ? "Existing key" : "Key"}
                  </th>
                  {kind === "serato" && <th className="px-3 py-2 font-medium">Status</th>}
                </tr>
              </thead>
              <tbody>
                {preview.map((t) => (
                  <tr key={t.id} className="border-b border-chassis last:border-0">
                    <td className="truncate px-3 py-2">{t.title || t.filename}</td>
                    <td className="px-3 py-2 font-data text-data-sm">
                      {t.bpm ? t.bpm.toFixed(1) : "—"}
                    </td>
                    <td className="px-3 py-2">
                      <KeyBadge code={t.camelot_key} keyName={t.key_name} />
                    </td>
                    {kind === "serato" && (
                      <td className="px-3 py-2">
                        {t.needs_analysis && (
                          <span className="rounded-sm bg-danger/15 px-2 py-0.5 text-data-sm font-medium text-danger">
                            needs_analysis
                          </span>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            type="button"
            onClick={commit}
            className="mt-4 inline-flex items-center gap-1.5 rounded-sm bg-led px-4 py-2 text-small font-semibold text-[#111111] transition-opacity hover:opacity-90"
          >
            Add {preview.length} track{preview.length === 1 ? "" : "s"} to library
            <ArrowRight size={15} />
          </button>
        </div>
      )}
    </div>
  );
}
