import { UploadCloud, Disc3, Waypoints, History, Settings } from "lucide-react";

const ITEMS = [
  { id: "import", label: "Import", icon: UploadCloud },
  { id: "library", label: "Library", icon: Disc3 },
  { id: "sort", label: "Sort", icon: Waypoints },
  { id: "history", label: "History", icon: History },
  { id: "settings", label: "Settings", icon: Settings },
];

export default function IconRail({ screen, onNavigate }) {
  return (
    <nav
      aria-label="Main"
      className="flex w-14 shrink-0 flex-col items-center gap-2 border-r border-chassis bg-panel py-4"
    >
      {ITEMS.map(({ id, label, icon: Icon }) => {
        const active = screen === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => onNavigate(id)}
            aria-label={label}
            aria-current={active ? "page" : undefined}
            title={label}
            className="group relative grid h-11 w-11 place-items-center rounded-sm text-ink/70 transition-colors hover:text-ink"
          >
            <Icon size={20} strokeWidth={active ? 2.25 : 1.75} className={active ? "text-led" : ""} />
            <span
              className={`absolute -bottom-0.5 h-0.5 w-6 rounded-full bg-led transition-opacity ${
                active ? "opacity-100" : "opacity-0"
              }`}
            />
            <span className="pointer-events-none absolute left-full ml-2 whitespace-nowrap rounded-sm border border-chassis bg-panel px-2 py-1 text-small opacity-0 shadow-float transition-opacity group-hover:opacity-100 z-20">
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
