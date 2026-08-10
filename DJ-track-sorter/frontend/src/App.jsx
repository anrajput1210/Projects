import { useCallback, useEffect, useState } from "react";
import TopBar from "./components/TopBar.jsx";
import IconRail from "./components/IconRail.jsx";
import Toast from "./components/Toast.jsx";
import { useTheme } from "./components/ThemeToggle/ThemeToggle.jsx";
import ImportScreen from "./screens/ImportScreen.jsx";
import LibraryScreen from "./screens/LibraryScreen.jsx";
import SortScreen from "./screens/SortScreen.jsx";
import HistoryScreen from "./screens/HistoryScreen.jsx";
import SettingsScreen from "./screens/SettingsScreen.jsx";
import BackendUnreachableScreen from "./screens/BackendUnreachableScreen.jsx";
import { usePlaylist } from "./state/usePlaylist.js";
import { checkHealth, exportRekordboxXml, exportM3u } from "./lib/api.js";

export default function App() {
  const [theme, setTheme] = useTheme();
  const [screen, setScreen] = useState("import");
  const [toast, setToast] = useState(null);
  const [events, setEvents] = useState([]);
  const [health, setHealth] = useState(null); // null = checking, true/false once known
  const [isRetrying, setIsRetrying] = useState(false);
  const [isExportingGlobal, setIsExportingGlobal] = useState(false);

  const playlist = usePlaylist();

  const logEvent = useCallback((message) => {
    setEvents((prev) => [...prev, { message, time: new Date().toLocaleTimeString([], { hour12: false }) }]);
  }, []);

  const showToast = useCallback((message, variant = "success") => {
    setToast({ message, variant });
    logEvent(message);
  }, [logEvent]);

  const pollHealth = useCallback(async () => {
    setIsRetrying(true);
    try {
      await checkHealth();
      setHealth(true);
    } catch {
      setHealth(false);
    } finally {
      setIsRetrying(false);
    }
  }, []);

  useEffect(() => {
    pollHealth();
    const interval = setInterval(pollHealth, 15000);
    return () => clearInterval(interval);
  }, [pollHealth]);

  function handleTracksAdded(tracks, files) {
    playlist.addTracks(tracks, files);
  }

  async function handleGlobalExport(kind) {
    if (!playlist.sortedTracks) return;
    setIsExportingGlobal(true);
    try {
      if (kind === "rekordbox") {
        await exportRekordboxXml(playlist.sortedTracks, "CRATEWHEEL Playlist");
        showToast("Rekordbox XML exported", "success");
      } else {
        await exportM3u(playlist.sortedTracks, "CRATEWHEEL Playlist");
        showToast("M3U exported", "success");
      }
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setIsExportingGlobal(false);
    }
  }

  if (health === false) {
    return (
      <div className="h-screen">
        <BackendUnreachableScreen onRetry={pollHealth} retrying={isRetrying} />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <TopBar
        theme={theme}
        onThemeChange={setTheme}
        canExport={Boolean(playlist.sortedTracks)}
        onExport={handleGlobalExport}
        isExporting={isExportingGlobal}
      />

      <div className="flex min-h-0 flex-1">
        <IconRail screen={screen} onNavigate={setScreen} />

        <main className="min-w-0 flex-1 overflow-y-auto">
          {screen === "import" && (
            <ImportScreen onTracksAdded={handleTracksAdded} onToast={showToast} />
          )}
          {screen === "library" && (
            <LibraryScreen
              pool={playlist.pool}
              audioUrls={playlist.audioUrls}
              onRemove={playlist.removeTrack}
              onAddTracks={handleTracksAdded}
              onNavigateSort={() => setScreen("sort")}
              onToast={showToast}
            />
          )}
          {screen === "sort" && (
            <SortScreen
              pool={playlist.pool}
              sortedTracks={playlist.sortedTracks}
              transitionByFromId={playlist.transitionByFromId}
              isSorting={playlist.isSorting}
              sortError={playlist.sortError}
              hasSorted={playlist.hasSorted}
              onSort={async () => {
                await playlist.runSort();
                logEvent(`Sorted ${playlist.pool.length} tracks`);
              }}
              onReorder={playlist.reorder}
              onToast={showToast}
            />
          )}
          {screen === "history" && <HistoryScreen events={events} />}
          {screen === "settings" && (
            <SettingsScreen theme={theme} onThemeChange={setTheme} health={health} />
          )}
        </main>
      </div>

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
