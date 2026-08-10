"use strict";

/* ---------------- Mobile nav toggle ---------------- */
(function () {
  const toggle = document.getElementById("navToggle");
  const nav = document.getElementById("mainNav");
  if (!toggle || !nav) return;

  toggle.addEventListener("click", () => {
    const open = document.body.classList.toggle("nav-open");
    toggle.setAttribute("aria-expanded", String(open));
    document.body.style.overflow = open ? "hidden" : "";
  });

  nav.querySelectorAll(".nav-link:not(.mega-trigger)").forEach((link) => {
    link.addEventListener("click", () => {
      document.body.classList.remove("nav-open");
      toggle.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
    });
  });
})();

/* ---------------- Mega menu ---------------- */
(function () {
  const isTouch = matchMedia("(hover: none), (pointer: coarse)").matches;
  document.querySelectorAll(".has-mega").forEach((item) => {
    const trigger = item.querySelector(".mega-trigger");
    if (!trigger) return;

    if (isTouch || matchMedia("(max-width: 980px)").matches) {
      trigger.addEventListener("click", () => {
        const open = item.classList.toggle("is-open");
        trigger.setAttribute("aria-expanded", String(open));
      });
    }
  });

  // Close any open mega-menu / mobile nav on outside click or Escape.
  document.addEventListener("click", (e) => {
    document.querySelectorAll(".has-mega.is-open").forEach((item) => {
      if (!item.contains(e.target)) {
        item.classList.remove("is-open");
        item.querySelector(".mega-trigger")?.setAttribute("aria-expanded", "false");
      }
    });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    document.querySelectorAll(".has-mega.is-open").forEach((item) => {
      item.classList.remove("is-open");
      item.querySelector(".mega-trigger")?.setAttribute("aria-expanded", "false");
    });
  });
})();

/* ---------------- FAQ accordion (one open at a time) ---------------- */
(function () {
  document.querySelectorAll(".faq-list").forEach((list) => {
    const items = Array.from(list.querySelectorAll(".faq-item"));
    items.forEach((item) => {
      const q = item.querySelector(".faq-q");
      const a = item.querySelector(".faq-a");
      if (!q || !a) return;
      q.addEventListener("click", () => {
        const willOpen = !item.classList.contains("is-open");
        items.forEach((other) => {
          other.classList.remove("is-open");
          other.querySelector(".faq-a").style.maxHeight = "";
          other.querySelector(".faq-q").setAttribute("aria-expanded", "false");
        });
        if (willOpen) {
          item.classList.add("is-open");
          q.setAttribute("aria-expanded", "true");
          a.style.maxHeight = a.scrollHeight + "px";
        }
      });
    });
  });
})();

/* ---------------- Scroll reveal ----------------
   Elements can opt in by hand with class="reveal", but the selectors below
   are also auto-tagged so every page animates consistently without each
   template repeating the class. Siblings stagger via a --reveal-i index. */
const REDUCED_MOTION = matchMedia("(prefers-reduced-motion: reduce)").matches;

(function () {
  const AUTO = [
    ".section-head",
    ".card",
    ".list-row",
    ".blog-card",
    ".cta-band",
    ".trust-bar span",
    ".contact-info-row",
    ".faq-item",
    ".map-placeholder",
    ".article-body > h2",
    ".disclaimer-note",
    ".assistant-shell",
    ".assistant-point",
  ];
  document.querySelectorAll(AUTO.join(",")).forEach((el) => el.classList.add("reveal"));

  // Stagger index is per-parent, so each row/grid cascades on its own.
  const seen = new Map();
  document.querySelectorAll(".reveal").forEach((el) => {
    const parent = el.parentElement;
    const i = seen.get(parent) || 0;
    seen.set(parent, i + 1);
    el.style.setProperty("--reveal-i", Math.min(i, 8));
  });

  const targets = document.querySelectorAll(".reveal");
  if (!targets.length) return;
  if (REDUCED_MOTION || !("IntersectionObserver" in window)) {
    targets.forEach((t) => t.classList.add("is-visible"));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -50px 0px" }
  );
  targets.forEach((t) => io.observe(t));
})();

/* ---------------- Count-up for stat numbers ----------------
   Preserves any non-numeric prefix/suffix ("20+" counts to 20, keeps "+"). */
(function () {
  const nums = document.querySelectorAll(".stat-card .num, .hero-meta strong");
  if (!nums.length || REDUCED_MOTION || !("IntersectionObserver" in window)) return;

  const run = (el) => {
    const raw = el.textContent.trim();
    const match = raw.match(/^(\D*)(\d+)(.*)$/);
    if (!match) return;
    const [, prefix, digits, suffix] = match;
    const target = parseInt(digits, 10);
    if (!target) return;

    const duration = 1100;
    const start = performance.now();
    const step = (now) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      el.textContent = prefix + Math.round(target * eased) + suffix;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          run(entry.target);
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.6 }
  );
  nums.forEach((n) => io.observe(n));
})();

/* ---------------- Scroll progress bar + condensed header ---------------- */
(function () {
  const bar = document.getElementById("scrollProgress");
  const header = document.querySelector(".site-header");
  if (!bar && !header) return;

  let ticking = false;
  const update = () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const y = window.scrollY;
    if (bar) bar.style.width = (max > 0 ? (y / max) * 100 : 0) + "%";
    if (header) header.classList.toggle("is-stuck", y > 40);
    ticking = false;
  };
  window.addEventListener(
    "scroll",
    () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(update);
      }
    },
    { passive: true }
  );
  update();
})();

/* ---------------- Hero parallax (pointer-driven, desktop only) ---------------- */
(function () {
  const hero = document.querySelector(".hero");
  const art = document.querySelector(".hero-art img");
  if (!hero || REDUCED_MOTION || matchMedia("(pointer: coarse)").matches) return;

  hero.addEventListener("pointermove", (e) => {
    const r = hero.getBoundingClientRect();
    const dx = (e.clientX - r.left) / r.width - 0.5;
    const dy = (e.clientY - r.top) / r.height - 0.5;
    hero.style.setProperty("--hero-shift", `translate3d(${dx * 26}px, ${dy * 18}px, 0)`);
    if (art) {
      art.style.setProperty("--art-x", `${dx * -18}px`);
      art.style.setProperty("--art-y", `${dy * -12}px`);
    }
  });
  hero.addEventListener("pointerleave", () => {
    hero.style.setProperty("--hero-shift", "translate3d(0,0,0)");
    if (art) {
      art.style.setProperty("--art-x", "0px");
      art.style.setProperty("--art-y", "0px");
    }
  });
})();

/* ---------------- Bar Council disclaimer modal ---------------- */
(function () {
  const modal = document.getElementById("disclaimerModal");
  const agree = document.getElementById("disclaimerAgree");
  if (!modal || !agree) return;

  const KEY = "col-disclaimer-agreed";
  try {
    if (!localStorage.getItem(KEY)) {
      modal.setAttribute("data-open", "true");
      document.body.style.overflow = "hidden";
    }
  } catch (_) {
    modal.setAttribute("data-open", "true");
  }

  agree.addEventListener("click", () => {
    modal.setAttribute("data-open", "false");
    document.body.style.overflow = "";
    try {
      localStorage.setItem(KEY, "1");
    } catch (_) {}
  });
})();

/* ---------------- Contact form -> Formspree ---------------- */
(function () {
  document.querySelectorAll("form[data-formspree]").forEach((form) => {
    const status = form.querySelector(".form-status");
    const submitBtn = form.querySelector("[type=submit]");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const endpoint = form.getAttribute("data-formspree");
      if (!endpoint || endpoint.includes("PLACEHOLDER_ID")) {
        showStatus(status, "error", "Form isn't connected yet — the firm needs to add their Formspree endpoint. See README.");
        return;
      }

      if (submitBtn) submitBtn.disabled = true;
      showStatus(status, null, "");

      try {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: { Accept: "application/json" },
          body: new FormData(form),
        });
        if (res.ok) {
          showStatus(status, "success", "Thank you — your message has been sent. We'll be in touch shortly.");
          form.reset();
        } else {
          showStatus(status, "error", "Something went wrong sending your message. Please try again or email us directly.");
        }
      } catch (_) {
        showStatus(status, "error", "Something went wrong sending your message. Please try again or email us directly.");
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  });

  function showStatus(el, type, message) {
    if (!el) return;
    el.classList.remove("is-success", "is-error");
    if (type) el.classList.add(`is-${type}`);
    el.textContent = message;
  }
})();

/* ---------------- Footer year ---------------- */
(function () {
  const el = document.getElementById("footYear");
  if (el) el.textContent = new Date().getFullYear();
})();

/* ---------------- Feature-detect backdrop-filter for the liquid-glass button ---------------- */
(function () {
  const supports =
    CSS.supports("backdrop-filter", "blur(1px)") || CSS.supports("-webkit-backdrop-filter", "blur(1px)");
  if (!supports) document.documentElement.classList.add("no-backdrop-filter");
})();
