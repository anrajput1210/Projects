const TABS = [
  { id: "upload", label: "Upload files" },
  { id: "rekordbox", label: "Rekordbox XML" },
  { id: "serato", label: "Serato crate" },
];

export default function ImportTabs({ active, onChange }) {
  return (
    <div role="tablist" aria-label="Import source" className="flex flex-wrap gap-2">
      {TABS.map((tab) => {
        const isActive = active === tab.id;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`rounded-full border px-4 py-1.5 text-small font-medium transition-colors ${
              isActive
                ? "border-led bg-led text-[#111111]"
                : "border-chassis bg-panel text-ink/70 hover:border-ink/40"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
