// 4-dot fill, quick-scan glanceable like a signal-strength icon —
// deliberately not a % bar (DESIGN.md §3.3).
export default function ConfidenceMeter({ value }) {
  if (value == null) {
    return <span className="text-data-sm text-ink/40">—</span>;
  }
  const filled = Math.max(0, Math.min(4, Math.round(value * 4)));
  return (
    <span
      className="inline-flex items-center gap-1"
      role="img"
      aria-label={`Confidence ${Math.round(value * 100)}%`}
      title={`${Math.round(value * 100)}% confidence`}
    >
      {Array.from({ length: 4 }, (_, i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: i < filled ? "var(--led)" : "var(--chassis)" }}
        />
      ))}
    </span>
  );
}
