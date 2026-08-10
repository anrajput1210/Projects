import { useRef, useState } from "react";
import TrackRow from "./TrackRow/TrackRow.jsx";

// Draggable ordered list, syncs to the dial. Keyboard equivalent: focus the
// grip handle, Arrow Up/Down moves the row (DESIGN.md §8).
export default function SortList({ tracks, transitionByFromId, activeId, onHover, onReorder }) {
  const [dragIndex, setDragIndex] = useState(null);
  const dragOverIndex = useRef(null);

  function handleDragStart(index) {
    setDragIndex(index);
  }

  function handleDragOver(e, index) {
    e.preventDefault();
    dragOverIndex.current = index;
  }

  function handleDrop(index) {
    if (dragIndex !== null && dragIndex !== index) {
      onReorder(dragIndex, index);
    }
    setDragIndex(null);
  }

  function handleKeyDown(e, index) {
    if (e.key === "ArrowUp" && index > 0) {
      e.preventDefault();
      onReorder(index, index - 1);
    } else if (e.key === "ArrowDown" && index < tracks.length - 1) {
      e.preventDefault();
      onReorder(index, index + 1);
    }
  }

  return (
    <div className="overflow-hidden rounded-md border border-chassis bg-panel">
      {tracks.map((track, index) => (
        <div
          key={track.id}
          draggable
          onDragStart={() => handleDragStart(index)}
          onDragOver={(e) => handleDragOver(e, index)}
          onDrop={() => handleDrop(index)}
          onDragEnd={() => setDragIndex(null)}
          className={dragIndex === index ? "opacity-40" : ""}
        >
          <TrackRow
            track={track}
            index={index}
            draggable
            dragHandleProps={{ onKeyDown: (e) => handleKeyDown(e, index) }}
            active={activeId === track.id}
            onHover={onHover}
            transition={
              transitionByFromId.get(track.id) &&
              transitionByFromId.get(track.id).to_id === tracks[index + 1]?.id
                ? transitionByFromId.get(track.id)
                : null
            }
          />
        </div>
      ))}
    </div>
  );
}
