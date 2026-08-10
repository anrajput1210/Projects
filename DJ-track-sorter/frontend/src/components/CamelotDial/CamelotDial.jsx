import { useEffect, useMemo, useState } from "react";
import { Disc3 } from "lucide-react";
import { camelotColor, camelotPosition, bpmDotRadius, CAMELOT_NUMBERS } from "../../lib/camelot.js";

const SIZE = 460;
const C = SIZE / 2;
const SECTOR_OUTER = 185;
const SECTOR_MID = 144;
const SECTOR_INNER = 102;
const HUB_R = 66;
const DOT_B_R = (SECTOR_OUTER + SECTOR_MID) / 2;
const DOT_A_R = (SECTOR_MID + SECTOR_INNER) / 2;
const LABEL_R = SECTOR_OUTER + 20;

function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handler = (e) => setReduced(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return reduced;
}

function sectorPath(startDeg, endDeg, rOuter, rInner) {
  const toXY = (deg, r) => {
    const rad = (deg * Math.PI) / 180;
    return [C + Math.cos(rad) * r, C + Math.sin(rad) * r];
  };
  const [x1, y1] = toXY(startDeg, rOuter);
  const [x2, y2] = toXY(endDeg, rOuter);
  const [x3, y3] = toXY(endDeg, rInner);
  const [x4, y4] = toXY(startDeg, rInner);
  return `M ${x1} ${y1} A ${rOuter} ${rOuter} 0 0 1 ${x2} ${y2} L ${x3} ${y3} A ${rInner} ${rInner} 0 0 0 ${x4} ${y4} Z`;
}

export default function CamelotDial({ tracks, order, spinning, activeId, onHoverTrack }) {
  const reducedMotion = useReducedMotion();

  const groups = useMemo(() => {
    const map = new Map();
    for (const t of tracks) {
      if (!t.camelot_key) continue;
      if (!map.has(t.camelot_key)) map.set(t.camelot_key, []);
      map.get(t.camelot_key).push(t);
    }
    return map;
  }, [tracks]);

  const dotPositions = useMemo(() => {
    const positions = new Map();
    for (const [key, group] of groups) {
      const base = camelotPosition(key, { outerR: DOT_B_R, innerR: DOT_A_R });
      if (!base) continue;
      group.forEach((track, i) => {
        const spread = Math.min(10, 3 * (group.length - 1));
        const offsetDeg = group.length > 1 ? -spread / 2 + (spread / (group.length - 1)) * i : 0;
        const angle = base.angle + (offsetDeg * Math.PI) / 180;
        const r = base.r;
        positions.set(track.id, {
          x: C + Math.cos(angle) * r,
          y: C + Math.sin(angle) * r,
        });
      });
    }
    return positions;
  }, [groups]);

  const activeTrack = tracks.find((t) => t.id === activeId) || null;

  const orderedForLine = useMemo(() => {
    if (!order) return [];
    return order.map((id) => dotPositions.get(id)).filter(Boolean);
  }, [order, dotPositions]);

  const hasTracks = tracks.some((t) => t.camelot_key);

  return (
    <div className="relative mx-auto" style={{ width: SIZE, maxWidth: "100%" }}>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="h-auto w-full"
        role="img"
        aria-label="Camelot key wheel showing analyzed tracks by key and BPM"
      >
        <g
          style={
            spinning && !reducedMotion
              ? { animation: "cratewheel-spin 90s linear infinite", transformOrigin: `${C}px ${C}px` }
              : undefined
          }
        >
          {/* sectors */}
          {CAMELOT_NUMBERS.map((n) => {
            const start = (n - 1) * 30 - 90 - 15;
            const end = start + 30;
            return (
              <g key={n}>
                <path
                  d={sectorPath(start, end, SECTOR_OUTER, SECTOR_MID)}
                  fill={camelotColor(`${n}B`)}
                  opacity={0.16}
                  stroke="var(--chassis)"
                  strokeWidth={1}
                />
                <path
                  d={sectorPath(start, end, SECTOR_MID, SECTOR_INNER)}
                  fill={camelotColor(`${n}A`)}
                  opacity={0.16}
                  stroke="var(--chassis)"
                  strokeWidth={1}
                />
              </g>
            );
          })}

          <circle cx={C} cy={C} r={SECTOR_INNER} fill="none" stroke="var(--chassis)" strokeWidth={1} />
          <circle cx={C} cy={C} r={SECTOR_OUTER} fill="none" stroke="var(--chassis)" strokeWidth={1} />

          {/* ring labels: text code always paired with sector color */}
          {CAMELOT_NUMBERS.map((n) => {
            const pos = camelotPosition(`${n}B`, { outerR: LABEL_R, innerR: LABEL_R });
            return (
              <text
                key={`label-${n}`}
                x={C + pos.x}
                y={C + pos.y}
                textAnchor="middle"
                dominantBaseline="middle"
                className="font-data"
                fontSize={11}
                fill="var(--ink)"
                opacity={0.7}
              >
                {n}B
              </text>
            );
          })}

          {/* connecting line: the traced set path */}
          {orderedForLine.length > 1 && (
            <polyline
              points={orderedForLine.map((p) => `${p.x},${p.y}`).join(" ")}
              fill="none"
              stroke="var(--led)"
              strokeWidth={1.5}
              strokeLinejoin="round"
              strokeLinecap="round"
              opacity={0.85}
              className="transition-all duration-200"
            />
          )}

          {/* track dots */}
          {tracks.map((t) => {
            const pos = dotPositions.get(t.id);
            if (!pos || !t.camelot_key) return null;
            const r = bpmDotRadius(t.bpm);
            const isActive = t.id === activeId;
            return (
              <circle
                key={t.id}
                cx={pos.x}
                cy={pos.y}
                r={isActive ? r + 2 : r}
                fill={camelotColor(t.camelot_key)}
                stroke={isActive ? "var(--ink)" : "var(--bg)"}
                strokeWidth={isActive ? 2 : 1.5}
                opacity={t.needs_analysis ? 0.25 : 1}
                className="cursor-pointer transition-all duration-200"
                onMouseEnter={() => onHoverTrack?.(t.id)}
                onMouseLeave={() => onHoverTrack?.(null)}
              >
                <title>
                  {(t.title || t.filename) + ` · ${t.camelot_key} · ${t.bpm ? Math.round(t.bpm) : "—"} BPM`}
                </title>
              </circle>
            );
          })}
        </g>

        {/* center hub — stays upright even while the ring spins */}
        <circle cx={C} cy={C} r={HUB_R} fill="var(--panel)" stroke="var(--chassis)" strokeWidth={1} />
      </svg>

      <div
        className="pointer-events-none absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center text-center"
        style={{ width: HUB_R * 1.7 }}
      >
        {!hasTracks ? (
          <>
            <Disc3 size={22} className="mb-1 text-chassis" />
            <p className="text-data-sm leading-tight text-ink/50">
              Import tracks to see them on the wheel
            </p>
          </>
        ) : activeTrack ? (
          <>
            <p className="w-full truncate text-small font-medium leading-tight">
              {activeTrack.title || activeTrack.filename}
            </p>
            <p className="mt-1 font-data text-data-sm text-ink/70">
              {activeTrack.camelot_key || "—"} · {activeTrack.bpm ? Math.round(activeTrack.bpm) : "—"} BPM
            </p>
            {activeTrack.key_confidence != null && (
              <p className="font-data text-data-sm text-ink/50">
                {Math.round(activeTrack.key_confidence * 100)}% conf.
              </p>
            )}
          </>
        ) : (
          <p className="font-data text-data-sm text-ink/50">{tracks.length} tracks</p>
        )}
      </div>

      {spinning && reducedMotion && (
        <div
          className="absolute left-1/2 top-[18%] h-3 w-3 -translate-x-1/2 animate-spin rounded-full border-2 border-chassis border-t-led"
          aria-hidden="true"
        />
      )}
    </div>
  );
}
