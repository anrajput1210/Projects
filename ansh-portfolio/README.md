# Ansh Rajput — Data Portfolio

Single-page portfolio built to `ansh-portfolio-design-spec.md`. Vanilla HTML/CSS/JS,
no build step — open `index.html` or serve the folder.

```
index.html    all three sections
style.css     palette + layout (spec Section 2 palette used verbatim)
script.js     drag props, mask reveal, scroll reveals, vignette
assets/       17 hand-drawn SVGs (hero props, doodles, 6 project visuals)
```

## Assets you should replace

Everything renders today, but three things are stand-ins:

| File | Replace with | Notes |
|---|---|---|
| `assets/headshot-placeholder.svg` | Real headshot | ~200×240, portrait. Swap the `src` on `.photo-real` in `index.html`. |
| `assets/mask-scribble.svg` | Optional | The doodle that covers the photo until it's dragged off. Keeps the "DRAG ME OFF" prompt — worth keeping. |
| `assets/signature.svg` | A scan of the real signature | Currently a hand-drawn approximation. |
| `assets/proj-*.svg` | Real chart/dashboard screenshots | Any aspect ratio works; keep ~170px of quiet space at the bottom for the caption band (see below). |

Project visuals are generated SVGs based on the resume metrics, not screenshots of the
actual work. Each reserves ~170 units of empty space at the bottom so the caption always
lands on clean background — preserve that when swapping in real screenshots, or the
caption will sit on top of chart detail.

## Content

All copy comes from the spec's Section 0 (name, contact, education, role, skills,
project metrics) and is used verbatim — no metrics were invented or paraphrased.

## Interactions

- **Drag** any hero prop (Pointer Events, so mouse/touch/pen share one path). No physics,
  no snapping. Position is seeded from `data-x`/`data-y` percentages, with
  `data-x-sm`/`data-y-sm` used below 620px.
- **Mask reveal**: drag the scribbled face more than 80px and it fades out permanently,
  exposing the photo. Below the threshold it springs back into play.
- **Scroll reveals**: `IntersectionObserver`, section columns staggered 100ms, skill list
  items 70ms apart, grid tiles 50ms.
- **Vignette**: fixed 150px fade-to-black at the viewport bottom, opacity tied to scroll
  progress through the end of the grid.
- `prefers-reduced-motion: reduce` disables every transition and shows all content.

## Deviations from the spec

Three, all forced by the content rather than preference:

1. **Magic UI MCP (spec Section 1a) was not reachable** in the environment this was built
   in, so no components were pulled. The hero drag, list/tile reveals and vignette are all
   hand-written per Sections 6 and 7. Anything sourced from a library would have been
   marked in a code comment; nothing is.
2. **Grid runs 3 columns, not 4.** With exactly 6 tiles the browser's column balancer packs
   them 2/2/2 and leaves the fourth column empty. One line in `style.css` (`.grid`) flips it
   back to 4 if more tiles get added.
3. **Skill list is ~33px, not the 48–64px the spec suggests.** "INFINITE HYPERPARAMETER
   TUNING" is 30 characters; at 48px+ it cannot hold one line in a half-viewport column.
   Below 620px it wraps instead.

## Browser support

Pointer Events, `IntersectionObserver`, CSS custom properties, CSS multi-column. Evergreen
browsers; a `matchMedia.addListener` fallback is in place for older Safari.
