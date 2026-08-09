#!/usr/bin/env node
/**
 * Zero-dependency static site builder for Chambers of Law.
 *
 * Each file under src/pages/** is a BODY fragment (not a full HTML doc),
 * preceded by an HTML-comment front-matter block:
 *
 *   <!--meta
 *   title: Page Title | Chambers of Law
 *   description: One-sentence meta description.
 *   nav: home
 *   -->
 *   <section>...actual page content...</section>
 *
 * build.js wraps that fragment with src/partials/head.html (which itself
 * contains the <title>/<meta description> placeholders), header.html,
 * footer.html and disclaimer-modal.html, marks the matching nav item
 * aria-current="page" via the `nav:` key, and writes the result to
 * dist/<same relative path>. assets/ is copied to dist/assets/ verbatim.
 *
 * Usage: node build.js
 */
"use strict";
const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const SRC_PAGES = path.join(ROOT, "src", "pages");
const PARTIALS_DIR = path.join(ROOT, "src", "partials");
const ASSETS_DIR = path.join(ROOT, "assets");
const DIST_DIR = path.join(ROOT, "dist");

const SITE_URL = "https://www.chambersoflaw.co.in"; // placeholder — see README

function readPartial(name) {
  return fs.readFileSync(path.join(PARTIALS_DIR, `${name}.html`), "utf8");
}

function rimraf(target) {
  if (fs.existsSync(target)) fs.rmSync(target, { recursive: true, force: true });
}

function walk(dir, exts) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full, exts));
    else if (exts.some((e) => entry.name.endsWith(e))) out.push(full);
  }
  return out;
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

function parseFrontMatter(raw) {
  const m = raw.match(/^<!--meta\s*([\s\S]*?)-->\s*([\s\S]*)$/);
  if (!m) throw new Error("Missing <!--meta ... --> front-matter block");
  const meta = {};
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^\s*([\w-]+)\s*:\s*(.+?)\s*$/);
    if (kv) meta[kv[1]] = kv[2];
  }
  return { meta, body: m[2].trim() };
}

function escapeAttr(str) {
  return String(str).replace(/"/g, "&quot;");
}

function render(template, vars) {
  return template.replace(/\{\{\s*([\w.-]+)\s*\}\}/g, (_, key) =>
    Object.prototype.hasOwnProperty.call(vars, key) ? vars[key] : ""
  );
}

function markActiveNav(headerHtml, navKey) {
  if (!navKey) return headerHtml;
  const re = new RegExp(`(data-nav="${navKey}"(?![\\w-]))`, "g");
  return headerHtml.replace(re, `$1 aria-current="page"`);
}

function build() {
  rimraf(DIST_DIR);
  fs.mkdirSync(DIST_DIR, { recursive: true });

  const headPartial = readPartial("head");
  const headerPartial = readPartial("header");
  const footerPartial = readPartial("footer");
  const disclaimerPartial = readPartial("disclaimer-modal");

  const pageFiles = walk(SRC_PAGES, [".html"]);
  let count = 0;

  for (const file of pageFiles) {
    const rel = path.relative(SRC_PAGES, file); // e.g. "about.html" or "blog/index.html"
    const raw = fs.readFileSync(file, "utf8");
    const { meta, body } = parseFrontMatter(raw);

    const urlPath = "/" + rel.replace(/\\/g, "/");
    const canonical = SITE_URL + (urlPath === "/index.html" ? "/" : urlPath);

    const head = render(headPartial, {
      title: meta.title || "Chambers of Law",
      description: meta.description || "",
      canonical,
    });

    const header = markActiveNav(headerPartial, meta.nav);

    const page = `<!doctype html>
<html lang="en">
<head>
${head}
</head>
<body>
${disclaimerPartial}
${header}
<main id="main">
${body}
</main>
${footerPartial}
<script src="/assets/js/main.js" defer></script>
</body>
</html>
`;

    const outPath = path.join(DIST_DIR, rel);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, page, "utf8");
    count++;
  }

  copyDir(ASSETS_DIR, path.join(DIST_DIR, "assets"));

  console.log(`Built ${count} page(s) into dist/`);
}

build();
