# Chambers of Law — Website Rebuild

## Context

The current site (chambersoflaw.co.in) is a ~2004-era design with image sliders, dated visuals, and a contact form of unknown reliability. The user's dad runs the firm (Chambers of Law, a boutique Indian IP/litigation firm est. 2004, offices in Ludhiana and Manchester, 6 named attorneys). Goal: rebuild it with a modern, professional dark-navy-and-gold design (based on a "Sterling & Finch" template the user adapted into a full design spec), keeping the real firm facts (practice areas, team, offices, contact details) but with entirely reworked visuals, structure, and copy. The user wants the **full** site rebuilt — not just a landing page — matching the current site's complete navigation depth (mega-menu detail pages, Acts/Resources, blog), plus a working contact form and a liquid-glass button micro-interaction.

Locked-in decisions from planning conversation:
- **Stack:** plain static HTML/CSS/JS. No React/Vue/Next/Tailwind/shadcn — chosen explicitly for simplicity of hosting/maintenance.
- **Content:** Claude drafts all copy (placeholder/informational, based on real firm facts + general IP-law knowledge) — user said "generate the content on your own."
- **Contact form:** must actually work, via Formspree (no backend needed).
- **Imagery:** no real photos exist — use abstract/illustrative graphics and icon/initials badges instead of photos, never fake stock photos of "attorneys."
- **Scope:** full site with all subpages + blog (not a one-pager) — ~29 HTML pages.
- **Buttons:** user shared a React/shadcn "liquid glass" button component for style reference. Since the site isn't React, the effect will be **ported to vanilla CSS/SVG/JS** (same inline SVG turbulence/displacement filter + backdrop-filter + hover/press states) rather than pulling in a React/Tailwind stack — user confirmed "whichever is easy and fast."

---

## 1. Project Location & Structure

New self-contained folder at workspace root (matching this workspace's convention of one top-level folder per project, e.g. `DJ-track-sorter/`, `moviechatAI/`): `chambers-of-law-website/`

```
chambers-of-law-website/
  build.js              # zero-dependency Node script (fs/path only)
  package.json          # single "build" script, no npm dependencies
  README.md             # setup, build, deploy, and "placeholders to replace" instructions
  .gitignore
  src/
    partials/
      head.html          # shared <head> meta/tag boilerplate
      header.html         # nav bar + mega-menu + mobile toggle
      footer.html          # footer columns + bottom bar
      disclaimer-modal.html # Bar Council gate modal
    pages/
      index.html, about.html, global-network.html, team.html,
      contact.html, privacy-policy.html, terms-of-service.html
      blog/               # index.html + 3 article pages
      know-more/          # 13 detail pages
      acts/               # 5 act-overview pages
  assets/
    css/
      tokens.css          # color/typography/spacing custom properties
      components.css      # buttons (incl. liquid-glass), cards, badges, accordion, mega-menu
      layout.css           # grid, section rhythm, page templates
    js/
      main.js             # nav toggle, mega-menu, FAQ accordion, scroll-reveal, disclaimer modal, Formspree submit
    icons/
      icons.svg           # sprite: scales, document, shield, globe, gavel, magnifier, chevron, arrow
      logo.svg             # wordmark + scales-of-justice glyph
  dist/                    # generated static output — the deployable site (committed, built via `node build.js`)
```

**Why a build script instead of duplicating HTML 29 times:** the nav (with a 14-item mega-menu), footer, and disclaimer modal are identical across every page. Hand-duplicating them across 29 files means every nav edit touches 29 files. `build.js` is a small, dependency-free Node script that does simple `{{> partial}}`-style string substitution to stitch `src/partials/*` + `src/pages/**/*` into plain static HTML files in `dist/`. The **output** is still 100% plain HTML/CSS/JS — deployable to any static host (Netlify, GitHub Pages, cPanel) with zero server or runtime build step required. Only the *authoring* process uses one script (`node build.js`, no `npm install` needed).

---

## 2. Design System (from user-provided spec)

- **tokens.css**: CSS custom properties for the full palette (`--color-bg-dark #0B0E14`, `--color-navy #1B2331`, `--color-gold #F2A93B`/`--color-gold-dark #D4922A`, `--color-ink #111318`, `--color-body-muted #6B7280`/`-dark #9CA3AF`, `--color-surface-tint #F5F6F8`, `--color-border-soft #E9EAEC`, etc.), type scale (headings: rounded-grotesque sans, 600–700 weight, 40–56px H1/32–40px H2; body: humanist sans 400–500, 15–17px/1.6 line-height), spacing/radius scale (pill = stadium radius, cards = 16–20px).
- **components.css**: eyebrow pill badges, list-row dividers, stat/feature/case/team cards (navy or gold solid fills with circular icon badges), FAQ accordion (numbered circular badges, rotating chevron), mega-menu dropdown, and buttons:
  - `.btn` (solid gold / outline variants)
  - `.btn-liquid-glass` — ported from the shared React reference: inline SVG `<filter>` (feTurbulence + feGaussianBlur + feDisplacementMap) applied via `backdrop-filter: url(#glass-filter)`, layered shadows for a frosted-glass edge, CSS `:hover` (brightness lift) and `:active` (scale-down) states. Applied to primary CTAs (Contact Us, Schedule Now).
- **Motion** (`main.js`): `IntersectionObserver`-based scroll reveal (fade + slight upward slide) per section; mega-menu slide-down on hover/tap; FAQ accordion expands one row at a time.
- **Layout**: max-width ~1200–1280px content, 12-column grid, alternating dark/white full-bleed sections per spec.

---

## 3. JS Behaviors (single `assets/js/main.js`, no bundler)

1. Mobile nav toggle (hamburger open/close)
2. Mega-menu open/close (hover on desktop, tap on mobile)
3. FAQ accordion (one open at a time, rotating chevron icon)
4. Scroll-reveal animation on section entry
5. Bar Council disclaimer modal — shows before hero renders on first visit, dismissal persisted via `localStorage` so it doesn't reappear every visit
6. Contact form → `fetch()` POST to Formspree endpoint, inline success/error state (no page reload)
7. Liquid-glass button: mostly CSS; JS only for touch-device detection to suppress hover-only states

---

## 4. Icons & Logo

Single inline SVG sprite (`assets/icons/icons.svg`) with `<symbol>` defs — scales-of-justice, document, shield, globe, gavel, magnifier, chevron-down, arrow-right, checkmark/seal — referenced via `<use>` across all pages. Logo (`assets/icons/logo.svg`): "Chambers of Law" wordmark in the heading font + a small gold scales-of-justice glyph. No external image assets needed for branding.

---

## 5. Formspree Integration

- Contact form (in `contact.html` and the homepage contact section) posts to a placeholder endpoint: `https://formspree.io/f/PLACEHOLDER_ID`.
- Displayed contact email uses a placeholder: `info@chambersoflaw.co.in`.
- `README.md` will document, step by step: sign up at formspree.io → create a form → replace `PLACEHOLDER_ID` (both locations) → replace the placeholder email site-wide → send a test submission to confirm delivery.

---

## 6. Build Order

1. Design tokens + base CSS + shared partials (header/mega-menu/footer/disclaimer modal) + icon sprite + logo + `build.js`
2. Homepage (`index.html`) — full section flow (hero → about → approach/expertise → work & vision → trust bar → practice areas → team teaser → insights teaser → FAQ → contact teaser → CTA band → footer)
3. Dedicated top-level pages: About Us, Global Network, Meet Our Team, Contact Us
4. "Know More" detail pages (13, one repeatable template: breadcrumb → hero banner → article body → related-links sidebar → CTA band)
5. Acts & Resources pages (5, same repeatable template)
6. Blog (listing page + 3 articles)
7. Legal pages (Privacy Policy, Terms of Service)
8. QA pass: nav/link consistency across all pages, responsive check, accessibility (contrast, focus states, alt text), disclaimer modal localStorage behavior, form submit test, `node build.js` clean run

---

## 7. Content Manifest — What Gets Written

All copy below is original, drafted by Claude from the current site's real facts plus general public knowledge of Indian IP law/process. It is **informational placeholder content for review**, not vetted legal advice — flagged clearly in the README for the firm to review before launch.

**Homepage** — hero (eyebrow + 3 rotating H1 lines + subhead + CTAs), about teaser + 3 stat cards (20+ years / 15+ practice areas / 6 attorneys), Approach + Expertise mini-cards, 3 illustrative case-highlight cards (generic/anonymized outcomes — *not real client matters*, must be swapped for real (or removed) before launch), trust-bar heading + 6 industry-sector labels, 6 practice-area list rows, team teaser, 3 blog teasers, 6-item FAQ, contact teaser, CTA band, footer columns.

**About Us** — expanded firm history/mission/values narrative (~400–600 words), fuller Approach/Expertise sections.

**Global Network** — India (Ludhiana) HQ + UK (Manchester) office blurbs, international trademark-filing capability note, both office addresses.

**Meet Our Team** — 3–4 sentence professional bio for each of the 6 named attorneys, using their real listed qualifications/roles (Rahul Rajput as founder gets fuller treatment) — clearly flagged as placeholder bios for the firm to personalize with real detail/photos.

**Contact Us** — form (Name/Email/Subject/Message → Formspree), both office addresses/phones, placeholder email, static map-style placeholder block.

**Blog** (listing + 3 original ~400–600 word articles, each with a "not legal advice" note):
1. *Nestlé Wins Trademark Battle Over KitKat Bar* — commentary on the real, publicly known Nestlé/KitKat shape-trademark disputes.
2. *Patents in India: A Growing Landscape* — general overview of Indian patent filing trends/policy.
3. *India Patent Authority and Big Pharma* — general overview of publicly known patent-policy/pharma tension (e.g. compulsory licensing, Section 3(d) debates).

**Know More — Trademarks group** (9 pages, ~300–500 words each: what/why/general process overview/disclaimer/CTA): About Trademarks, Documents for Registration, FAQ on Trademarks (expanded, 8–10 Q&As), Geographical Indications, Process of Registration, Trade Mark Searching, Trade Mark Watching Service, Trademark as Domain, Trademark Opposition.

**Know More — IP & Related group** (4 pages, same format): Intellectual Property (overview), About Copyright, Industrial Design, Patent.

**Acts & Resources** (5 pages, ~200–350 words each — purpose/scope only, not statutory text reproduction): Indian Trade Marks Act, Indian Patents Act, Indian Copyright Act, Designs Act, Trade Marks Rules. *Note: the spec footer names "New Trademark Rules 2015" — the rules actually in force are the Trade Marks Rules, 2017. I'll write accurate, current content and flag this naming discrepancy for the firm's review rather than silently perpetuating outdated info.*

**Legal pages** — Privacy Policy (data collected via contact form, localStorage disclosure, no third-party sharing beyond Formspree) and Terms of Service (standard site-use terms, no attorney-client relationship formed by browsing, governing law India) — standard boilerplate.

**Disclaimer Modal** — standard Bar Council of India advertising-restriction text (informational only, not solicitation, no attorney-client relationship until formal engagement), "I Agree" gate, localStorage-persisted.

---

## 8. Caveats to Flag in README

- All page copy is original draft content for review — not legal advice, must be reviewed by an Indian-qualified advocate before publishing (especially bios, Acts/Rules pages, process/timeline claims, and the illustrative case-highlight examples).
- Case-highlight examples are generic/illustrative, not real matters — replace or remove before launch to avoid any compliance concern with fabricated results.
- All imagery is abstract/illustrative (no photos) — swap in real team headshots/office photos before launch.
- Formspree endpoint and contact email are placeholders — must be replaced with real values before launch.

---

## 9. Verification

- Run `node build.js` → generates `dist/`.
- Serve locally (`npx serve dist` or `python -m http.server` from `dist/`) and click through: full nav + mega-menu on every page, all internal links (Know More, Acts, Blog, footer columns), FAQ accordion, disclaimer modal (including that it doesn't reappear after localStorage dismissal + reload), mobile nav toggle at a narrow viewport, contact form submission (expected to fail gracefully until a real Formspree ID is added — verify the error state looks intentional, not broken).
- Responsive check at common breakpoints (mobile/tablet/desktop).
- Confirm no console errors and that `node build.js` re-runs cleanly (idempotent, no leftover stale files in `dist/`).
