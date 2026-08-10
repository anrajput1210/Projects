import { Clock } from "lucide-react";

export default function HistoryScreen({ events }) {
  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-h1 font-semibold">History</h1>
      <p className="mt-2 text-small text-ink/50">
        This session's activity only — nothing's persisted server-side.
      </p>

      {events.length === 0 ? (
        <div className="mt-10 flex flex-col items-center gap-3 rounded-md border border-chassis bg-panel py-16 text-center">
          <Clock size={26} className="text-chassis" />
          <p className="text-small text-ink/50">Nothing's happened yet this session.</p>
        </div>
      ) : (
        <ul className="mt-6 divide-y divide-chassis rounded-md border border-chassis bg-panel">
          {events
            .slice()
            .reverse()
            .map((event, i) => (
              <li key={i} className="flex items-center justify-between gap-3 px-4 py-3">
                <span className="text-small">{event.message}</span>
                <span className="shrink-0 font-data text-data-sm text-ink/40">{event.time}</span>
              </li>
            ))}
        </ul>
      )}

      <p className="mt-6 text-data-sm text-ink/40">
        Nothing's saved — refreshing clears your session.
      </p>
    </div>
  );
}
