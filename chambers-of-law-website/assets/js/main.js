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

/* ---------------- Scroll reveal ---------------- */
(function () {
  const targets = document.querySelectorAll(".reveal");
  if (!targets.length) return;
  if (!("IntersectionObserver" in window)) {
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
    { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
  );
  targets.forEach((t) => io.observe(t));
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
