# Chambers of Law — Website

A full rebuild of the Chambers of Law website: plain static HTML/CSS/JS, no framework, built via a small zero-dependency Node script. See [PLAN.md](PLAN.md) for the original design/content brief this was built from.

## Requirements

Just [Node.js](https://nodejs.org) (any recent version). No `npm install` is needed — `build.js` uses only Node's built-in `fs`/`path` modules.

## Building the site

```
node build.js
```

This regenerates `dist/` from scratch every time (safe to re-run, always clean — no stale leftover files). `dist/` is the deployable output: plain HTML/CSS/JS, no build step needed at deploy time.

## Previewing locally

`dist/` uses root-relative paths (`/assets/...`) and the icon sprite is referenced via `<use href="/assets/icons/icons.svg#...">`, which requires the page to be served over HTTP — opening the HTML file directly (`file://`) will not render the icons correctly in most browsers. Serve it locally with any static server, for example:

```
npx serve dist
```

or, with Node already installed and nothing else:

```
node -e "require('http').createServer((q,s)=>require('fs').readFile('dist'+(q.url==='/'?'/index.html':q.url.split('?')[0]),(e,d)=>{if(e){s.writeHead(404);s.end('404')}else{s.end(d)}})).listen(8080)"
```

Then visit `http://localhost:8080`.

## Project structure

```
build.js                  # the static site builder (see comment at top of the file)
src/
  partials/                # head.html, header.html (nav + mega-menu), footer.html, disclaimer-modal.html
  pages/                    # one file per page — see "How pages work" below
assets/
  css/
    tokens.css              # design tokens (colour, type, spacing, radius, motion)
    layout.css              # reset, base typography, grid, section rhythm, page templates
    components.css          # buttons, cards, nav/mega-menu, footer, accordion, forms, modal
    assistant.css           # the Legal Assistant section shell (see below)
    animations.css          # motion layer — loaded last so it can refine resting styles
  js/main.js                # nav toggle, mega-menu, FAQ accordion, scroll-reveal + stagger,
                            # stat count-up, scroll progress, hero parallax, disclaimer modal, form submit
  icons/                    # icons.svg (sprite), logo.svg (standalone wordmark), favicon.svg
  img/                      # authored SVG artwork (see "Artwork" below)
dist/                       # generated output — do not hand-edit, it's overwritten on every build
```

## How pages work

Every file in `src/pages/**/*.html` is a **body fragment**, not a full HTML document. Each one starts with an HTML-comment front-matter block:

```html
<!--meta
title: Page Title | Chambers of Law
description: One-sentence meta description for search engines / social previews.
nav: about
-->
<section class="page-hero">
  ...actual page content...
</section>
```

`build.js` reads that front matter, wraps the rest of the file with the shared head/header/footer/disclaimer partials, and writes the result to `dist/` at the same relative path. The `nav:` key (optional) marks the matching item in the header as the current page (`aria-current="page"`) — use the same key as the `data-nav="..."` attribute on the corresponding link in `src/partials/header.html` (e.g. `home`, `about`, `team`, `blog`, `contact`, or `resources` for anything under Know More/Acts).

To add a new page: create a new `.html` fragment under `src/pages/` (or a subfolder) with that front-matter block, link to it from wherever makes sense (nav, footer, related-reading sidebars), and run `node build.js`.

## Before this goes live — placeholders to replace

This site was built with **entirely original placeholder content** (drafted from the firm's real public facts plus general IP-law knowledge) and needs a firm review pass before publishing. Specifically:

1. **Formspree endpoint.** The contact form (`src/pages/contact.html`) posts to `https://formspree.io/f/PLACEHOLDER_ID`. Sign up at [formspree.io](https://formspree.io), create a form, and replace `PLACEHOLDER_ID` in that file. Until this is done, the form will show a graceful inline error rather than actually failing silently — that's intentional, not a bug.
2. **Contact email.** `info@chambersoflaw.co.in` appears in `contact.html` and `src/partials/footer.html` — confirm or replace.
3. **Office addresses & phone numbers.** Both offices (Ludhiana and Manchester) currently show bracketed placeholders like `[Office Address Line 1]` in `global-network.html` and `contact.html` — fill in the real addresses/phone numbers.
4. **Team bios.** `team.html` and the homepage team teaser have placeholder names/bios for 5 of the 6 attorneys (only Rahul Rajput, as founder, is named) — real names, qualifications, enrolment years, and headshots need to be added. No real attorney photos exist yet, so all "photos" are currently letter-badge placeholders by design.
5. **Illustrative case highlights.** The three "representative matters" cards on the homepage are explicitly generic/anonymised examples, not real client matters — replace with real (anonymised, client-consented) results or remove them before launch, to avoid any compliance issue with fabricated outcomes.
6. **Blog articles.** The three blog posts are original commentary on real, publicly reported disputes/policy topics (Nestlé/KitKat, Indian patent filing trends, Section 3(d) and compulsory licensing) — reviewed for general accuracy but not vetted as legal-grade citations. Have an Indian-qualified advocate review before publishing, especially the Acts/Rules pages and any process/timeline claims.
7. **Canonical domain.** `build.js` hardcodes `https://www.chambersoflaw.co.in` as the site's canonical URL base (used for `<link rel="canonical">` and Open Graph tags) — update the `SITE_URL` constant near the top of `build.js` if that's not the final domain.
8. **Dates.** Privacy Policy and Terms of Service both have a `[Date to be set by the firm before publishing]` placeholder for "last updated."

## Legal Assistant

The homepage has a **Legal Assistant** section (`#legal-assistant`, styled by `assets/css/assistant.css`). It ships as a **shell only** — the panel frame, heading, disclaimer strip, and an empty mount point. There is deliberately no chatbot wired up yet.

To add one, render it into the mount point and delete the placeholder:

```html
<!-- src/pages/index.html -->
<div id="legal-assistant-mount">
  <!-- delete .assistant-placeholder, mount your widget here -->
</div>
```

```js
// or from JS, wherever your widget initialises
const mount = document.getElementById("legal-assistant-mount");
mount.innerHTML = "";           // clear the "coming soon" placeholder
myChatbot.render(mount);
```

The mount is a flex container filling the remaining panel height, so a child with `flex: 1` will fill it correctly.

**Two things to keep when you wire a real assistant in:**

1. **Leave the disclaimer strip in place.** Under Bar Council of India advertising and solicitation rules, an assistant on a law firm's site should present general information only and must not read as legal advice or as creating an attorney–client relationship.
2. **Be careful with an LLM-backed bot on a static site.** There's no backend here, so calling a model API from the page would expose your API key to anyone who views source. If you want a generative assistant, route it through a serverless function (Netlify/Vercel function, Cloudflare Worker) that holds the key server-side — and have an advocate review the system prompt and its guardrails before it goes live.

## Artwork

All imagery is original SVG authored for this site — there are no photographs or stock images, and nothing depicts a real person:

| File | Used on |
| --- | --- |
| `assets/img/hero-emblem.svg` | Homepage hero — scales of justice within orbiting rings |
| `assets/img/cover-trademark.svg` | Blog cover — the KitKat/shape-mark article |
| `assets/img/cover-patents.svg` | Blog cover — the patent filing trends article |
| `assets/img/cover-policy.svg` | Blog cover — the pharma patent policy article |
| `assets/img/network-arc.svg` | Global Network page — Manchester ↔ Ludhiana arc |

Each file carries its own CSS animation *inside* the SVG (which still runs when referenced via `<img>`) and its own `prefers-reduced-motion` guard, so they hold still for visitors who ask for reduced motion. They're vector, so they stay sharp at any size and need no responsive image sizes.

## Motion

`assets/css/animations.css` plus the motion code in `main.js` provide: a scroll progress bar, a condensing header, hero entrance and pointer parallax, scroll-reveal with per-row stagger, count-up on the stat numbers, mega-menu cascade, and hover states throughout.

Reveal animation is applied **automatically** — `main.js` tags a list of selectors (`.card`, `.section-head`, `.list-row`, `.blog-card`, and so on) with the `reveal` class, so new pages animate without adding classes by hand. Add `class="reveal"` manually only for an element outside that list.

Every effect is disabled under `prefers-reduced-motion: reduce`, and content is guaranteed visible rather than stuck at `opacity: 0` (verified in QA).

## Deploying

`dist/` is a plain static site — deploy it as-is to Netlify, GitHub Pages, Vercel, S3, or a standard cPanel host. There's no server-side runtime requirement. Re-run `node build.js` and redeploy `dist/` whenever content changes.

## Notes on specific features

- **Bar Council of India disclaimer modal** — shown on first visit, dismissal persisted via `localStorage` (`col-disclaimer-agreed`) so it doesn't reappear on later visits. Clear that key (or use a private/incognito window) to test the first-visit state again.
- **Liquid-glass button** (`.btn-liquid-glass`, used for "Schedule Now" CTAs) — a frosted/refractive effect built from `backdrop-filter` plus an inline SVG `<filter>` (feTurbulence + feDisplacementMap) defined in `header.html`. Degrades gracefully to a plain frosted button in browsers without `backdrop-filter` support (detected in `main.js`, adds a `.no-backdrop-filter` class to `<html>`).
- **Mega-menu** — hover-driven on desktop, tap-to-expand on mobile/touch (`main.js` detects `pointer: coarse` / narrow viewports).
