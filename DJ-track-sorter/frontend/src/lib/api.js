const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function parseJsonOrThrow(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with status ${response.status}`);
  }
  return response.json();
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) throw new Error(`status ${response.status}`);
  return response.json().catch(() => ({}));
}

export async function uploadTracks(files, onProgress) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  if (onProgress && typeof XMLHttpRequest !== "undefined") {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE_URL}/api/upload`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded / e.total);
      };
      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText);
          if (xhr.status >= 200 && xhr.status < 300) resolve(data.tracks);
          else reject(new Error(data.detail || `Request failed with status ${xhr.status}`));
        } catch {
          reject(new Error(`Request failed with status ${xhr.status}`));
        }
      };
      xhr.onerror = () => reject(new Error("Upload failed"));
      xhr.send(formData);
    });
  }

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });

  const data = await parseJsonOrThrow(response);
  return data.tracks;
}

export async function importRekordboxXml(file) {
  const formData = new FormData();
  formData.append("files", file);

  const response = await fetch(`${API_BASE_URL}/api/import/rekordbox`, {
    method: "POST",
    body: formData,
  });

  const data = await parseJsonOrThrow(response);
  return data.tracks;
}

export async function importSeratoCrate(file) {
  const formData = new FormData();
  formData.append("files", file);

  const response = await fetch(`${API_BASE_URL}/api/import/serato`, {
    method: "POST",
    body: formData,
  });

  const data = await parseJsonOrThrow(response);
  return data.tracks;
}

export async function sortTracks(tracks) {
  const response = await fetch(`${API_BASE_URL}/api/sort`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tracks }),
  });

  return parseJsonOrThrow(response);
}

async function downloadExport(path, tracks, playlistName, fallbackFilename) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tracks, playlist_name: playlistName }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Export failed with status ${response.status}`);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fallbackFilename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function exportRekordboxXml(tracks, playlistName) {
  return downloadExport("/api/export/rekordbox", tracks, playlistName, "cratewheel-playlist.xml");
}

export function exportM3u(tracks, playlistName) {
  return downloadExport("/api/export/m3u", tracks, playlistName, "cratewheel-playlist.m3u");
}
