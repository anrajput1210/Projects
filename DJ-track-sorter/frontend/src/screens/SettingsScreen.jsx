import ThemeToggle from "../components/ThemeToggle/ThemeToggle.jsx";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function SettingsScreen({ theme, onThemeChange, health }) {
  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-h1 font-semibold">Settings</h1>

      <div className="mt-6 divide-y divide-chassis rounded-md border border-chassis bg-panel">
        <div className="flex items-center justify-between px-4 py-4">
          <div>
            <p className="text-small font-medium">Appearance</p>
            <p className="text-data-sm text-ink/50">Light / dark mode</p>
          </div>
          <ThemeToggle theme={theme} onChange={onThemeChange} />
        </div>

        <div className="flex items-center justify-between px-4 py-4">
          <div>
            <p className="text-small font-medium">Backend</p>
            <p className="font-data text-data-sm text-ink/50">{API_BASE_URL}</p>
          </div>
          <span
            className={`h-2 w-2 rounded-full ${health ? "bg-led" : "bg-danger"}`}
            aria-label={health ? "Connected" : "Unreachable"}
            title={health ? "Connected" : "Unreachable"}
          />
        </div>

        <div className="px-4 py-4">
          <p className="text-small font-medium">Data</p>
          <p className="mt-1 text-data-sm text-ink/50">
            No accounts, no database. Your playlist lives only in this browser tab —
            refreshing clears it. Uploaded audio is analyzed and discarded, never stored.
          </p>
        </div>
      </div>
    </div>
  );
}
