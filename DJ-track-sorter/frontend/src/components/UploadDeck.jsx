import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";

// Dropzone styled with turntable chassis borders + screw-dot corners — a
// light skeuomorphic quote, not a full illustration (DESIGN.md §4).
export default function UploadDeck({ accept, multiple = false, hint, onFiles, disabled }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) onFiles(files);
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={hint}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) inputRef.current?.click();
      }}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={`relative rounded-md border-2 border-dashed p-10 text-center transition-colors ${
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"
      } ${dragOver ? "border-led bg-led/5" : "border-chassis bg-panel hover:border-ink/30"}`}
    >
      {/* screw-dot corners */}
      {["top-2 left-2", "top-2 right-2", "bottom-2 left-2", "bottom-2 right-2"].map((pos) => (
        <span
          key={pos}
          className={`absolute ${pos} h-1.5 w-1.5 rounded-full bg-chassis`}
          aria-hidden="true"
        />
      ))}

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        className="sr-only"
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          if (files.length) onFiles(files);
          e.target.value = "";
        }}
      />

      <UploadCloud size={28} className="mx-auto mb-3 text-ink/40" strokeWidth={1.5} />
      <p className="text-body font-medium">{hint}</p>
      <p className="mt-1 text-small text-ink/50">Click or drop to browse</p>
    </div>
  );
}
