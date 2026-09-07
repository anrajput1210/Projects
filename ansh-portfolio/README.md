# Ansh Rajput — Data Portfolio

Single-page portfolio built to `ansh-portfolio-design-spec.md`. Vanilla HTML/CSS/JS,
no build step — open `index.html` or serve the folder.

```
index.html    hero, connect strip, skills split, project grid, case-study panel
style.css     palette + layout (spec Section 2 palette used verbatim)
script.js     drag props, mask reveal, scroll reveals, vignette,
              live GitHub layer, tile tilt, FLIP case-study expansion
assets/       headshot + 19 hand-drawn SVGs
```

## Assets you should replace

Everything renders today, but some pieces are still stand-ins:

| File | Status | Notes |
|---|---|---|
| `assets/headshot.jpg` | **Real** | Supplied by Ansh. Square 400×400, cropped to 4:5 via `object-fit` with `object-position: center 18%` so the crop lands on the face. Swap in a portrait-orientation original and that bias can be dropped. |
| `assets/Ansh_Rajput_Data_Analyst.pdf` | **MISSING** | The Resume card links here and the link is dead until you add the file. Drop the real PDF at exactly this path — no code change needed. |
| `assets/resume-thumb.svg` | Placeholder | A drawn approximation of the resume page layout, used for the card preview. Replace with a rendered first page of the real PDF for an exact preview. |
| `assets/signature.svg` | Placeholder | Hand-drawn approximation; replace with a scan. |
| `assets/proj-*.svg` | Placeholder | Generated from resume metrics, not screenshots of the actual work. Any aspect ratio works; keep ~170 units of quiet space at the bottom for the caption band. |
| `assets/mask-scribble.svg` | Keep | The scribbled yellow marker smiley covering the photo until dragged off. Wordless by design - the spec calls for a graphic, not a labelled card. Sized to 118% of the photo so its wobbled edge clears the frame corners and the photo is genuinely hidden. |
| `assets/contrib-scaffold.svg` | Keep | Deliberately uniform — it is the placeholder shown until the live GitHub graph loads, so it must not imply activity data that was never fetched. |

## Copy that still needs Ansh's approval

The six **PROBLEM** lines shown in the expanded case studies are drafts written for this
build — the design spec flags them as drafts too. They are **not** resume copy. Find them
as `.detail-problem` in `index.html` and rewrite in your own words before this goes public.

Everything else — name, contact, education, skills, project metrics, resume bullets — is
verbatim from the spec's Section 0 and Section 5a.

Two phrasings are load-bearing and should not be softened:

- Education is always **"currently studying / expected graduation May 2027"**, never
  "graduated" or a bare "class of 2027".
- Grant Thornton Bharat is always **past tense** (`PREVIOUSLY`, "Interned in Gurugram"),
  never a current role.

## Interactions

- **Drag** any hero prop (Pointer Events, so mouse/touch/pen share one path). No physics,
  no snapping. Position is seeded from `data-x`/`data-y` percentages, with
  `data-x-sm`/`data-y-sm` used below 620px.
- **Mask reveal**: drag the yellow scribble smiley more than 80px and it fades out over
  300ms and stops taking pointer events, exposing the photo for good. Below the threshold
  it stays in play.
- **Connect strip**: all three cards are real `<a href>` elements first. The GitHub
  contributions graph and the repo/language stats are fetched at runtime and layered on
  top; if either request fails the scaffold and `—` placeholders simply stay.
- **Tile hover**: cursor-tracked tilt (±5°) and a spotlight that follows the pointer.
  Fine pointers only.
- **Case study expansion**: clicking a tile runs a FLIP flight from the tile's exact grid
  rect into the panel (560ms, ease-out-expo), then the copy assembles — title, then a
  typewritten PROBLEM line at +150ms, then tech chips flying in 40ms apart at +300ms, then
  bullets with self-drawing markers 80ms apart at +450ms. Close via the X, the backdrop or
  Escape reverses the same flight. Below 760px it becomes a bottom sheet instead.
- **Scroll reveals**: `IntersectionObserver`, section columns staggered 100ms, skill list
  items 70ms apart, grid tiles 50ms.
- **Vignette**: fixed 150px fade-to-black at the viewport bottom, opacity tied to scroll
  progress through the end of the grid.
- `prefers-reduced-motion: reduce` disables every transition and shows all content.

## Progressive enhancement

Nothing important is locked behind JS or the network:

- Case-study copy sits in the markup as `.tile-detail` and is **visible** when JS is off;
  the `js` class added at boot is what hides it and arms the expansion.
- The same `js` gate arms the scroll-reveal hidden states, so a script failure leaves the
  page fully readable rather than blank.
- Connect cards work as plain links with no JS and no network.
- Backdrop blur is skipped on devices reporting ≤4 cores, so the expansion animation is
  never traded for the effect.

## Deviations from the spec

1. **Magic UI MCP (spec Section 1a) was not reachable** in the environment this was built
   in, so the full-catalog browse the spec asks for did not happen and no components were
   pulled. The connect strip, the case-study expansion, the hero drag, the reveals and the
   vignette are all hand-written per Sections 3, 3a, 5a, 6 and 7. Anything library-sourced
   would carry a code comment; nothing does. **Worth redoing that pass** in an environment
   where the MCP is available — the strip and the expansion are the two places it would
   most likely have earned its keep.
2. **Grid runs 3 columns, not 4.** With exactly 6 tiles the browser's column balancer packs
   them 2/2/2 and leaves the fourth column empty. One line in `style.css` (`.grid`) flips it
   back to 4 if more tiles get added.
3. **Headline ceiling is 100px.** "PROBLEM SOLVING CHILD" is 21 characters against the
   source headline's 13. At the source's size it runs off the viewport, so the clamp
   ceiling came down to hold it on one line at the same proportions.
4. **Skill list is ~33px, not the 48–64px the spec suggests.** "MASTER DATA MANAGEMENT" is
   22 characters; at 48px+ it cannot hold one line in a half-viewport column. Below 620px
   it wraps instead.
5. **GPA and dates moved to the connect strip.** The spec's hero block has no room for
   them, but they are real resume data, so they sit under the 2027 callout rather than
   being dropped.

## Typography

Per the spec's fidelity requirement the whole UI is **Helvetica Neue**, system-font-first:

```
--sans     "Helvetica Neue", HelveticaNeue, Helvetica, Inter, Arial, sans-serif
--display  same family at weight 900 (headline, skill list, stat number, panel title)
--code     IBM Plex Mono - the terminal-style PROBLEM line only
--hand     Caveat - positioning statement and the SOLVING ? annotation
--marker   Permanent Marker - the I WORK WITH header
```

Helvetica Neue is a system font on macOS and is not on Google Fonts, so **Inter** (800/900)
is loaded as the fallback for machines without it, as the spec directs. The small
NAME/TOPIC/REACH AT labels are this same family at medium weight with extra letter-spacing
- deliberately *not* a monospace face, which is what the source does.

The three project SVGs that carried a hard-coded `Archivo Black` were updated to the same
Helvetica stack. Note that an SVG referenced through `<img>` cannot load a webfont at all,
so those labels always render in a locally installed face.

## Browser support

Pointer Events, `IntersectionObserver`, Web Animations API (`Element.animate`), CSS custom
properties, CSS multi-column. Evergreen browsers; a `matchMedia.addListener` fallback is in
place for older Safari. `backdrop-filter` degrades to a plain scrim where unsupported.
