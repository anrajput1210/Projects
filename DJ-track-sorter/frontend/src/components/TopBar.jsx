import { useState, useRef, useEffect } from "react";
import { Disc3, FileCode, ListMusic, ChevronDown } from "lucide-react";
import ThemeToggle from "./ThemeToggle/ThemeToggle.jsx";

export default function TopBar({ theme, onThemeChange, canExport, onExport, isExporting }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return;
    function onDocClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [menuOpen]);

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-chassis bg-panel px-4">
      <div className="flex items-center gap-2.5">
        <Disc3 size={22} className="text-led" strokeWidth={1.75} aria-hidden="true" />
        <span className="font-display text-[0.8rem] tracking-wide">CRATEWHEEL</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            disabled={!canExport || isExporting}
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-1.5 rounded-sm border border-chassis px-3 py-1.5 text-small font-medium text-ink transition-colors enabled:hover:border-led disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isExporting ? "Exporting…" : "Export"}
            <ChevronDown size={14} />
          </button>
          {menuOpen && canExport && (
            <div className="absolute right-0 top-full z-20 mt-1 w-48 rounded-md border border-chassis bg-panel py-1 shadow-float">
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  onExport("rekordbox");
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-small hover:bg-bg"
              >
                <FileCode size={15} /> Rekordbox XML
              </button>
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  onExport("m3u");
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-small hover:bg-bg"
              >
                <ListMusic size={15} /> M3U
              </button>
            </div>
          )}
        </div>
        <ThemeToggle theme={theme} onChange={onThemeChange} />
      </div>
    </header>
  );
}
