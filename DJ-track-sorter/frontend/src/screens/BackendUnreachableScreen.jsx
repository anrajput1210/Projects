import { RefreshCw } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function BackendUnreachableScreen({ onRetry, retrying }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-5 bg-bg px-6 text-center">
      <svg width="140" height="140" viewBox="0 0 140 140" aria-hidden="true">
        <circle cx="70" cy="70" r="62" fill="var(--panel)" stroke="var(--chassis)" strokeWidth="2" />
        <circle cx="70" cy="70" r="42" fill="none" stroke="var(--chassis)" strokeWidth="1" />
        <circle cx="70" cy="70" r="26" fill="none" stroke="var(--chassis)" strokeWidth="1" />
        <circle cx="70" cy="70" r="5" fill="var(--chassis)" />
        {/* tonearm, lifted off the record */}
        <g stroke="var(--danger)" strokeWidth="3" strokeLinecap="round" fill="none">
          <line x1="118" y1="34" x2="96" y2="58" />
          <line x1="118" y1="34" x2="126" y2="20" />
        </g>
        <circle cx="118" cy="34" r="5" fill="var(--panel)" stroke="var(--danger)" strokeWidth="2" />
      </svg>

      <div>
        <p className="font-display text-eyebrow uppercase text-danger">Connection lost</p>
        <h1 className="mt-3 text-h1 font-semibold">Can't reach the sorter backend</h1>
        <p className="mt-2 font-data text-data-sm text-ink/50">
          Is it running on {API_BASE_URL}?
        </p>
      </div>

      <button
        type="button"
        onClick={onRetry}
        disabled={retrying}
        className="flex items-center gap-1.5 rounded-sm bg-led px-4 py-2 text-small font-semibold text-[#111111] transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        <RefreshCw size={15} className={retrying ? "animate-spin" : ""} />
        {retrying ? "Checking…" : "Retry"}
      </button>
    </div>
  );
}
