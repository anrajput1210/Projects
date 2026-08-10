import { camelotColor } from "../lib/camelot.js";

export default function KeyBadge({ code, keyName }) {
  if (!code) {
    return <span className="font-data text-data-sm text-ink/40">···</span>;
  }

  return (
    <span className="inline-flex items-center gap-1.5" title={keyName || undefined}>
      <span
        className="h-2.5 w-2.5 shrink-0 rounded-full"
        style={{ background: camelotColor(code) }}
        aria-hidden="true"
      />
      <span className="font-data text-data-sm font-medium">{code}</span>
    </span>
  );
}
