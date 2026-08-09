import { useRef, useState } from "react";
import { uploadTracks } from "../api.js";

const ACCEPTED_EXTENSIONS = ".mp3,.wav,.flac";

export default function UploadPanel({ onTracksUploaded }) {
  const inputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);

  async function handleFiles(fileList) {
    const files = Array.from(fileList);
    if (files.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      const tracks = await uploadTracks(files);
      onTracksUploaded(tracks);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="panel">
      <h2>Upload tracks</h2>
      <p className="hint">
        MP3, WAV, or FLAC. Add as many tracks as you want — up to 5GB each.
        Files are analyzed and discarded, nothing is stored.
      </p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        multiple
        disabled={isUploading}
        onChange={(e) => handleFiles(e.target.files)}
      />
      {isUploading && <p className="status">Uploading…</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
