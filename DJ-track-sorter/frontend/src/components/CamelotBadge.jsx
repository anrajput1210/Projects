import { camelotColor } from "../camelot.js";

export default function CamelotBadge({ code, keyName }) {
  if (!code) {
    return <span className="camelot-badge camelot-badge--empty">—</span>;
  }

  const { background, text } = camelotColor(code);

  return (
    <span
      className="camelot-badge"
      style={{ background, color: text }}
      title={keyName || undefined}
    >
      {code}
    </span>
  );
}
