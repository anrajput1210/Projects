// Camelot Wheel color helper for the UI. Same hue for the A (minor) and B
// (major) side of each number, distinguished by lightness — mirrors the
// convention DJ software (e.g. Mixed In Key) uses so a familiar "color
// wheel" mental model carries over.
const CODE_PATTERN = /^(\d{1,2})([AB])$/;

export function camelotColor(code) {
  const match = code && CODE_PATTERN.exec(code);
  if (!match) return { background: "#4a4658", text: "#ffffff" };

  const num = parseInt(match[1], 10);
  const letter = match[2];
  const hue = ((num - 1) * 30) % 360;
  const lightness = letter === "A" ? 40 : 62;
  const textColor = lightness > 55 ? "#1a1a1a" : "#ffffff";

  return {
    background: `hsl(${hue}, 70%, ${lightness}%)`,
    text: textColor,
  };
}

export function transitionColor(score) {
  if (score >= 0.8) return "#3ecf6e";
  if (score >= 0.5) return "#e8b93e";
  if (score > 0) return "#e8743e";
  return "#6b6779";
}
