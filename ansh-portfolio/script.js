/* ===========================================================
   ANSH RAJPUT — DATA PORTFOLIO
   Custom interaction layer. Everything here is hand-written:
   the Magic UI MCP referenced in the design spec (Section 1a)
   was not reachable in this environment, so the hero drag,
   the list/tile reveals and the scroll-linked vignette all use
   the vanilla approach described in Sections 6 and 7.
   =========================================================== */

(function () {
  'use strict';

  // marks that JS is live, which is what arms the pre-reveal hidden states
  document.documentElement.classList.add('js');

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* --------------------------------------------------------
     1. Hero props — free drag, no physics, no snapping.
     Pointer Events cover mouse, touch and pen in one path.
     -------------------------------------------------------- */

  var stage = document.getElementById('stage');
  var hint = document.getElementById('heroHint');
  var mask = document.getElementById('photoMask');
  var MASK_REVEAL_DISTANCE = 80; // px, per spec
  var topZ = 20;
  var hasDragged = false;

  /* Seed each prop's starting position from its data-x / data-y (percentages).
     Narrow screens use the data-x-sm / data-y-sm pair so the props clear the
     headline instead of piling on top of it. A prop the visitor has already
     moved keeps where they put it. */
  var smallScreen = window.matchMedia('(max-width: 620px)');

  function seedPositions() {
    var small = smallScreen.matches;
    document.querySelectorAll('.draggable').forEach(function (el) {
      if (el.dataset.moved === 'true') return;
      var x = (small && el.dataset.xSm) ? el.dataset.xSm : el.dataset.x;
      var y = (small && el.dataset.ySm) ? el.dataset.ySm : el.dataset.y;
      el.style.left = x + '%';
      el.style.top = y + '%';
    });
  }

  seedPositions();
  if (smallScreen.addEventListener) {
    smallScreen.addEventListener('change', seedPositions);
  } else if (smallScreen.addListener) {
    smallScreen.addListener(seedPositions);   // Safari < 14
  }

  function makeDraggable(el, opts) {
    opts = opts || {};
    var dx = 0, dy = 0;          // committed offset
    var startX = 0, startY = 0;  // pointer origin
    var originX = 0, originY = 0;
    var pointerId = null;

    function onDown(e) {
      if (el.dataset.locked === 'true') return;
      if (opts.stopBubble) e.stopPropagation();
      pointerId = e.pointerId;
      startX = e.clientX;
      startY = e.clientY;
      originX = dx;
      originY = dy;
      el.classList.add('is-dragging');
      el.dataset.moved = 'true';
      if (!opts.keepZ) el.style.zIndex = ++topZ;
      el.setPointerCapture(pointerId);
      e.preventDefault();

      if (!hasDragged) {
        hasDragged = true;
        if (hint) hint.classList.add('is-hidden');
      }
    }

    function onMove(e) {
      if (pointerId === null || e.pointerId !== pointerId) return;
      dx = originX + (e.clientX - startX);
      dy = originY + (e.clientY - startY);
      el.style.setProperty('--dx', dx + 'px');
      el.style.setProperty('--dy', dy + 'px');
      if (opts.onMove) opts.onMove(dx, dy);
    }

    function onUp(e) {
      if (pointerId === null || e.pointerId !== pointerId) return;
      el.classList.remove('is-dragging');
      try { el.releasePointerCapture(pointerId); } catch (err) { /* already gone */ }
      pointerId = null;
      if (opts.onRelease) opts.onRelease(dx, dy);
    }

    el.addEventListener('pointerdown', onDown);
    el.addEventListener('pointermove', onMove);
    el.addEventListener('pointerup', onUp);
    el.addEventListener('pointercancel', onUp);
    el.addEventListener('dragstart', function (e) { e.preventDefault(); });
  }

  if (stage) {
    document.querySelectorAll('.draggable').forEach(function (el) { makeDraggable(el); });
  }

  /* The scribbled mask over the headshot: same drag engine, plus the
     one-way reveal. Dragged more than 80px from its start, it fades
     out for good and the photo underneath stays visible. */
  if (mask) {
    var revealed = false;
    makeDraggable(mask, {
      stopBubble: true,   // don't drag the photo along with the mask
      keepZ: true,
      onMove: function (dx, dy) {
        if (revealed) return;
        if (Math.sqrt(dx * dx + dy * dy) > MASK_REVEAL_DISTANCE) {
          revealed = true;
          mask.dataset.locked = 'true';
          mask.classList.add('is-lifted');
          mask.setAttribute('aria-hidden', 'true');
        }
      }
    });
  }

  /* --------------------------------------------------------
     2. Scroll reveals — Section 2 columns and grid tiles.
     -------------------------------------------------------- */

  function observe(nodes, onEnter) {
    if (!('IntersectionObserver' in window) || reduceMotion) {
      nodes.forEach(function (n) { n.classList.add('is-revealed'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        onEnter(entry.target);
        io.unobserve(entry.target);
      });
    }, { threshold: 0.18, rootMargin: '0px 0px -8% 0px' });
    nodes.forEach(function (n) { io.observe(n); });
  }

  // Section 2: left/right staggered ~100ms; skill list items stagger in one at a time.
  var columns = Array.prototype.slice.call(document.querySelectorAll('.split .reveal'));
  columns.forEach(function (col) {
    col.querySelectorAll('.skill-list li').forEach(function (li, i) {
      li.style.transitionDelay = (i * 70) + 'ms';
    });
  });
  observe(columns, function (col) {
    var delay = parseInt(col.dataset.revealDelay || '0', 10);
    setTimeout(function () { col.classList.add('is-revealed'); }, delay);
  });

  // Section 3: tiles fade in, staggered ~50ms each.
  var tiles = Array.prototype.slice.call(document.querySelectorAll('.tile'));
  tiles.forEach(function (t, i) { t.style.transitionDelay = (i % 4) * 50 + 'ms'; });
  observe(tiles, function (t) { t.classList.add('is-revealed'); });

  /* --------------------------------------------------------
     3. Bottom-of-grid vignette — opacity tracks scroll progress
     through the last screenful of the project grid.
     -------------------------------------------------------- */

  var gridSection = document.getElementById('work-grid');
  var vignette = document.getElementById('vignette');

  if (gridSection && vignette) {
    var ticking = false;

    function updateVignette() {
      var rect = gridSection.getBoundingClientRect();
      var vh = window.innerHeight;
      // distance of the section's end above the fold, normalised over one viewport
      var progress = 1 - Math.min(Math.max((rect.bottom - vh) / vh, 0), 1);
      vignette.style.opacity = progress.toFixed(3);
      ticking = false;
    }

    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(updateVignette);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    updateVignette();
  }
})();
