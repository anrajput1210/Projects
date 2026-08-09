export default function SortControls({ onSort, disabled, isSorting }) {
  return (
    <div className="sort-controls">
      <p className="hint">
        Orders your set for harmonic mixing, weighing both Camelot key
        compatibility and BPM closeness together.
      </p>
      <button type="button" onClick={onSort} disabled={disabled || isSorting}>
        {isSorting ? "Sorting…" : "Sort playlist"}
      </button>
      {disabled && <p className="hint">Add at least 2 tracks to sort.</p>}
    </div>
  );
}
