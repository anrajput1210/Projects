// Camelot Wheel math: color generation + polar layout for the dial.
// hue = (camelotNumber - 1) * 30deg, walked evenly around the 12 spokes;
// B (major, outer ring) is fully saturated, A (minor, inner ring) desaturated
// — this is what keeps the wheel reading as a real color wheel instead of an
// arbitrary palette (DESIGN.md §1.2).
const CODE_PATTERN = /^(\d{1,2})([AB])$/i;

export function parseCamelot(code) {
  const match = code && CODE_PATTERN.exec(code.trim());
  if (!match) return null;
  return { number: parseInt(match[1], 10), letter: match[2].toUpperCase() };
}

export function camelotColor(code) {
  const parsed = parseCamelot(code);
  if (!parsed) return "hsl(0 0% 55%)";
  const { number, letter } = parsed;
  const hue = (number - 1) * 30;
  const sat = letter === "B" ? 68 : 42;
  const light = letter === "B" ? 52 : 46;
  return `hsl(${hue} ${sat}% ${light}%)`;
}

export function transitionColor(score) {
  if (score >= 0.8) return "#3ecf6e";
  if (score >= 0.5) return "#e8b93e";
  if (score > 0) return "#e8743e";
  return "var(--chassis)";
}

// Position a key on the dial: B keys sit on the outer ring, A keys inner.
// Angle 0 (1B) points straight up, like the real Camelot chart.
export function camelotPosition(code, { outerR, innerR }) {
  const parsed = parseCamelot(code);
  if (!parsed) return null;
  const { number, letter } = parsed;
  const angle = ((number - 1) * 30 - 90) * (Math.PI / 180);
  const r = letter === "B" ? outerR : innerR;
  return {
    x: Math.cos(angle) * r,
    y: Math.sin(angle) * r,
    angle,
    r,
  };
}

// Normalized dot radius from BPM, clamped so a 200 BPM track doesn't blow
// past a sane on-wheel size (DESIGN.md §2).
export function bpmDotRadius(bpm, { min = 60, max = 190, rMin = 4, rMax = 11 } = {}) {
  if (!bpm) return rMin;
  const clamped = Math.min(Math.max(bpm, min), max);
  const t = (clamped - min) / (max - min);
  return rMin + t * (rMax - rMin);
}

export const CAMELOT_NUMBERS = Array.from({ length: 12 }, (_, i) => i + 1);
