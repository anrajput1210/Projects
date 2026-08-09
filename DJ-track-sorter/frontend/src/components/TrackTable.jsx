import { Fragment } from "react";
import CamelotBadge from "./CamelotBadge.jsx";
import { transitionColor } from "../camelot.js";

function formatDuration(sec) {
  if (sec === null || sec === undefined) return "—";
  const minutes = Math.floor(sec / 60);
  const seconds = Math.round(sec % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export default function TrackTable({ tracks, transitions, onRemove }) {
  const transitionByFromId = new Map((transitions || []).map((t) => [t.from_id, t]));
  const columnCount = onRemove ? 7 : 6;

  return (
    <table className="track-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Key</th>
          <th>BPM</th>
          <th>Title</th>
          <th>Artist</th>
          <th>Duration</th>
          {onRemove && <th></th>}
        </tr>
      </thead>
      <tbody>
        {tracks.map((track, index) => {
          const transition = transitionByFromId.get(track.id);
          return (
            <Fragment key={track.id}>
              <tr>
                <td>{index + 1}</td>
                <td>
                  <CamelotBadge code={track.camelot_key} keyName={track.key_name} />
                </td>
                <td>{track.bpm ? track.bpm.toFixed(1) : "—"}</td>
                <td>
                  {track.title || track.filename}
                  {track.needs_analysis && <span className="needs-analysis"> needs audio</span>}
                </td>
                <td>{track.artist || "—"}</td>
                <td>{formatDuration(track.duration_sec)}</td>
                {onRemove && (
                  <td>
                    <button
                      type="button"
                      className="remove-btn"
                      onClick={() => onRemove(track.id)}
                      aria-label={`Remove ${track.filename}`}
                    >
                      ×
                    </button>
                  </td>
                )}
              </tr>
              {transition && (
                <tr className="transition-row">
                  <td colSpan={columnCount}>
                    <span
                      className="transition-dot"
                      style={{ background: transitionColor(transition.score) }}
                    />
                    mix score {Math.round(transition.score * 100)}%
                    <span className="transition-detail">
                      (key {Math.round(transition.key_score * 100)}% · bpm{" "}
                      {Math.round(transition.bpm_score * 100)}%)
                    </span>
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
