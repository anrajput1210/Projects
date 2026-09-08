# Ansh Rajput — Data Portfolio

Single-page portfolio built to `ansh-portfolio-design-spec.md`. Vanilla HTML/CSS/JS,
no build step — open `index.html` or serve the folder.

```
index.html    hero, connect strip, skills split, project grid, case-study panel
style.css     palette + layout (spec Section 2 palette used verbatim)
script.js     drag props, mask reveal, scroll reveals, vignette,
              live GitHub layer, tile tilt, FLIP case-study expansion
assets/       resume PDF + 17 hand-drawn SVGs
```

## Assets you should replace

Everything renders today, but some pieces are still stand-ins:

| File | Status | Notes |
|---|---|---|
| `assets/Ansh_Rajput_Data_Analyst.pdf` | **Real** | Ansh's resume, linked by the Resume card. Replace this file in place when the resume is updated — the path is what the card points at, so no code change is needed. |
| `assets/resume-thumb.svg` | Placeholder | A drawn approximation of the resume page, used for the card preview — it mirrors the real document's section order but is not a render of it. No PDF rasteriser (Ghostscript / pdftoppm / ImageMagick) was available on this machine to produce a true first-page image; install one and replace this file for an exact preview. |
| `assets/signature.svg` | Placeholder | Hand-drawn approximation; replace with a scan. |
| `assets/proj-*.svg` | Placeholder | Generated from resume metrics, not screenshots of the actual work. Any aspect ratio works; keep ~170 units of quiet space at the bottom for the caption band. |
| `assets/caret-scribble.svg`, `assets/face-doodle.svg` | Keep | The hand-drawn caret and little face that sit with the SOLVING ? annotation over the headline. |
| `assets/contrib-scaffold.svg` | Keep | Deliberately uniform — it is the placeholder shown until the live GitHub graph loads, so it must not imply activity data that was never fetched. |

## Analytics

Google Analytics 4 (`G-BDFLTRV0MZ`) is loaded from the document head in `index.html`.
It is blocked by the Content-Security-Policy in the Claude artifact preview, which does
not allow `googletagmanager.com`, so page views only register on the real host.

## Copy that still needs Ansh's approval

The six **PROBLEM** lines shown in the expanded case studies are drafts written for this
build — the design spec flags them as drafts too. They are **not** resume copy. Find them
as `.detail-problem` in `index.html` and rewrite in your own words before this goes public.

Everything else — name, contact, education, skills, project metrics, resume bullets — is
verbatim from the resume PDF. Note that the design spec's transcription differed from the
actual PDF in several places; the PDF won each time:

- the Grant Thornton internship ran **July 13 – September 13, 2026**, not June–Aug
- LSTM mean absolute error is **~$2.10 per share**, not "under $2/share"
- three bullets had been trimmed (the LSTM model is built **in TensorFlow/Keras**,
  the regime chart uses **Matplotlib**, ranking quality used **precision@10 and
  recall@10**, and the Power BI work **drove adoption of standardized validation checks**)

**The project grid holds personal projects only.** Grant Thornton is an internship, not a
project, so it has no tile - the grid carries the five projects from the resume's PROJECTS
section. The internship still appears where it belongs, as work history in the
`PREVIOUSLY` block on the positioning card.

Two phrasings are load-bearing and should not be softened:

- Education is always **"currently studying / expected graduation May 2027"**, never
  "graduated" or a bare "class of 2027".
- Grant Thornton Bharat is always **past tense** (`PREVIOUSLY`, "Interned in Gurugram"),
  never a current role.

## Interactions

- **Drag** any hero prop (Pointer Events, so mouse/touch/pen share one path). No physics,
  no snapping. Position is seeded from `data-x`/`data-y` percentages, with
  `data-x-sm`/`data-y-sm` used below 620px.
- **Drag the headline** too - both words and the handwritten annotation move as one block.
  Only the glyphs take the pointer, not the full-width `h1` box, so the empty band beside
  the text stays click-through to whatever is behind it. At rest the headline is wall text
  sitting behind the props; grabbing it lifts `.hero-title` above them so it is never
  dragged out of sight.
- `.stage` is a positioning container only and is `pointer-events: none`. It spans the
  whole hero, so if it took events it would swallow every click meant for anything painted
  beneath it. The props opt back in individually.
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

## The headline

`PROBLEM CHILD` is set as three flex children: the two words either side of a `.headline-gap`
that is only `.3em` wide - a word space, not a hole. The handwritten `SOLVING ?` annotation
is absolutely positioned off that gap at `bottom: 100%`, so it floats above the line and
spans across both words rather than pushing them apart. The caret hangs off its underside
and points down into the gap; the small sketched face sits beside the question mark.

## The hero room

The backdrop is two planes rather than a flat fill:

- **Wall** - `.hero` background, soft blue-grey darkening from `#bcc7cb` to `#a3afb5`.
- **Seam** - `.hero-floor::before`, a blurred shadow band straddling the 80% line so the
  wall meets the floor as a gradual transition, never an edge.
- **Floor** - `.hero-floor`, from 80% to the bottom, slightly lighter than the wall.
- **Vignette** - `.hero::before`, a corner darkening that makes the wall read as an
  enclosed space. It sits above the floor and below every content layer, so it shades the
  room without dimming the text.
- **Contact shadows** - a blurred radial `::after` under each prop that stands on the
  floor. The signature hangs on the wall and deliberately gets none.
- The chart printout uses `perspective(520px) rotateX(62deg)`, a short enough perspective
  distance that the top edge is visibly narrower than the bottom - laid flat and receding
  toward the wall rather than a flat rectangle.

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
2. **Grid runs 3 columns, not 4.** The browser's column balancer leaves a fourth column
   empty at this tile count. One line in `style.css` (`.grid`) flips it back to 4 if enough
   tiles get added to fill it.
3. **Skill list is ~33px, not the 48–64px the spec suggests.** "MASTER DATA MANAGEMENT" is
   22 characters; at 48px+ it cannot hold one line in a half-viewport column. Below 620px
   it wraps instead.
4. **GPA and dates moved to the connect strip.** The spec's hero block has no room for
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
