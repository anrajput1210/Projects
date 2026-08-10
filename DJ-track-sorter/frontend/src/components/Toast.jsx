import { useEffect } from "react";
import { CheckCircle2, AlertCircle, X } from "lucide-react";

function timestamp() {
  return new Date().toLocaleTimeString([], { hour12: false });
}

export default function Toast({ toast, onDismiss }) {
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => onDismiss(), 4000);
    return () => clearTimeout(timer);
  }, [toast, onDismiss]);

  if (!toast) return null;
  const Icon = toast.variant === "error" ? AlertCircle : CheckCircle2;

  return (
    <div className="fixed bottom-4 left-4 z-50 flex items-center gap-2.5 rounded-md border border-chassis bg-panel px-3.5 py-2.5 shadow-float cratewheel-fade">
      <Icon
        size={16}
        className={toast.variant === "error" ? "text-danger" : "text-led"}
        aria-hidden="true"
      />
      <span className="text-small">{toast.message}</span>
      <span className="font-data text-data-sm text-ink/40">{timestamp()}</span>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="ml-1 text-ink/40 hover:text-ink"
      >
        <X size={14} />
      </button>
    </div>
  );
}
