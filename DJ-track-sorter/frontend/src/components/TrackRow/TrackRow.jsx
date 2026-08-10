import { useRef } from "react";
import { Play, Pause, X, GripVertical, UploadCloud } from "lucide-react";
import KeyBadge from "../KeyBadge.jsx";
import ConfidenceMeter from "../ConfidenceMeter.jsx";
import { transitionColor } from "../../lib/camelot.js";

function formatDuration(sec) {
  if (sec === null || sec === undefined) return "—";
  const minutes = Math.floor(sec / 60);
  const seconds = Math.round(sec % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export default function TrackRow({
  track,
  index,
  isPlaying,
  hasAudio,
  onTogglePlay,
  onRemove,
  onUploadAudio,
  transition,
  draggable = false,
  dragHandleProps,
  active,
  onHover,
}) {
  const fileRef = useRef(null);
  const lowConfidence = track.key_confidence != null && track.key_confidence < 0.5;

  return (
    <div
      onMouseEnter={() => onHover?.(track.id)}
      onMouseLeave={() => onHover?.(null)}
      className={`group flex items-center gap-3 border-b border-chassis px-3 py-2.5 last:border-0 ${
        lowConfidence ? "border-dashed" : ""
      } ${active ? "bg-led/5" : ""} ${track.needs_analysis ? "opacity-70" : ""}`}
    >
      {draggable && (
        <button
          type="button"
          {...dragHandleProps}
          aria-label={`Reorder ${track.title || track.filename}`}
          className="shrink-0 cursor-grab text-ink/30 hover:text-ink/70 active:cursor-grabbing"
        >
          <GripVertical size={16} />
        </button>
      )}

      {typeof index === "number" && (
        <span className="w-5 shrink-0 font-data text-data-sm text-ink/40">{index + 1}</span>
      )}

      <button
        type="button"
        onClick={() => hasAudio && onTogglePlay?.(track.id)}
        disabled={!hasAudio}
        aria-label={hasAudio ? (isPlaying ? "Pause preview" : "Play preview") : "No audio in memory"}
        className={`grid h-7 w-7 shrink-0 place-items-center rounded-full border border-chassis ${
          hasAudio ? "text-ink hover:border-led hover:text-led" : "text-ink/20"
        }`}
      >
        {isPlaying ? <Pause size={12} /> : <Play size={12} />}
      </button>

      <div className="min-w-0 flex-1">
        <p className="truncate text-small font-medium">{track.title || track.filename}</p>
        <p className="truncate text-data-sm text-ink/50">{track.artist || "—"}</p>
      </div>

      <div className="w-16 shrink-0">
        <KeyBadge code={track.camelot_key} keyName={track.key_name} />
      </div>

      <div className="w-14 shrink-0 font-data text-data-sm">
        {track.bpm ? track.bpm.toFixed(1) : "—"}
      </div>

      <div className="w-12 shrink-0 font-data text-data-sm text-ink/50">
        {formatDuration(track.duration_sec)}
      </div>

      <div className="w-16 shrink-0">
        <ConfidenceMeter value={track.key_confidence} />
      </div>

      {transition && (
        <div className="hidden w-28 shrink-0 items-center gap-1.5 sm:flex">
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: transitionColor(transition.score) }}
          />
          <span className="font-data text-data-sm text-ink/60">
            {Math.round(transition.score * 100)}% mix
          </span>
        </div>
      )}

      {track.needs_analysis && (
        <>
          <span className="shrink-0 rounded-sm bg-danger/15 px-2 py-0.5 text-data-sm font-medium text-danger">
            needs audio
          </span>
          <input
            ref={fileRef}
            type="file"
            accept=".mp3,.wav,.flac"
            className="sr-only"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUploadAudio?.(track, file);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="flex shrink-0 items-center gap-1 rounded-sm border border-chassis px-2 py-1 text-data-sm text-ink/70 hover:border-led hover:text-led"
          >
            <UploadCloud size={12} /> Upload audio
          </button>
        </>
      )}

      {onRemove && (
        <button
          type="button"
          onClick={() => onRemove(track.id)}
          aria-label={`Remove ${track.title || track.filename}`}
          className="shrink-0 text-ink/30 opacity-0 hover:text-danger group-hover:opacity-100"
        >
          <X size={15} />
        </button>
      )}
    </div>
  );
}
