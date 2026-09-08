/* ===========================================================
   ANSH RAJPUT — DATA PORTFOLIO
   Custom interaction layer. Everything here is hand-written:
   the Magic UI MCP referenced in the design spec (Section 1a)
   was not reachable in this environment, so the hero drag, the
   list/tile reveals, the scroll-linked vignette, the connect
   strip and the case-study expansion all use the vanilla
   approach described in Sections 3, 3a, 5a, 6 and 7.
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

  /* The headline drags as one block - both words plus the handwritten
     annotation - using the same engine as the props. keepZ because it
     lives in its own stacking context and cannot be raised past it. */
  var headline = document.querySelector('.headline');
  var heroTitle = document.querySelector('.hero-title');
  if (headline) {
    makeDraggable(headline, { keepZ: true });
    // .headline cannot escape .hero-title's stacking context, so the lift
    // has to happen on the wrapper
    headline.addEventListener('pointerdown', function () {
      if (heroTitle) heroTitle.style.zIndex = ++topZ;
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

  /* --------------------------------------------------------
     4. Connect strip (Section 3a) — live GitHub layer.
     The cards are real links already; this only adds data on
     top. Every failure path leaves the resting state intact.
     -------------------------------------------------------- */

  var GH_USER = 'anrajput1210';
  var contribLive = document.getElementById('contribLive');

  if (contribLive) {
    contribLive.addEventListener('load', function () {
      contribLive.classList.add('is-loaded');
    });
    // on error the scaffold underneath simply stays visible
    contribLive.src = 'https://ghchart.rshah.org/8fa38c/' + GH_USER;
  }

  var ghStats = document.getElementById('ghStats');
  if (ghStats && window.fetch) {
    var setStat = function (key, value) {
      var node = ghStats.querySelector('[data-gh="' + key + '"]');
      if (node && value) node.textContent = value;
    };

    fetch('https://api.github.com/users/' + GH_USER)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) setStat('repos', d.public_repos); })
      .catch(function () { /* placeholder dash stays */ });

    fetch('https://api.github.com/users/' + GH_USER + '/repos?per_page=100&sort=pushed')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (repos) {
        if (!repos || !repos.length) return;
        var tally = {};
        repos.forEach(function (repo) {
          if (repo.language) tally[repo.language] = (tally[repo.language] || 0) + 1;
        });
        var top = Object.keys(tally).sort(function (a, b) { return tally[b] - tally[a]; })[0];
        setStat('lang', top);
      })
      .catch(function () { /* placeholder dash stays */ });
  }

  /* --------------------------------------------------------
     5. Tile hover — cursor-tracked tilt + spotlight.
     Fine pointers only; a touch device never gets a hover
     state worth paying for.
     -------------------------------------------------------- */

  var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  var TILT = 5; // degrees at the tile edge

  if (finePointer.matches && !reduceMotion) {
    tiles.forEach(function (tile) {
      var inner = tile.querySelector('.tile-inner');
      if (!inner) return;

      tile.addEventListener('pointermove', function (e) {
        var r = tile.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width;
        var py = (e.clientY - r.top) / r.height;
        inner.style.setProperty('--ry', ((px - 0.5) * 2 * TILT).toFixed(2) + 'deg');
        inner.style.setProperty('--rx', ((0.5 - py) * 2 * TILT).toFixed(2) + 'deg');
        inner.style.setProperty('--spot-x', (px * 100).toFixed(1) + '%');
        inner.style.setProperty('--spot-y', (py * 100).toFixed(1) + '%');
      });

      tile.addEventListener('pointerleave', function () {
        inner.style.setProperty('--rx', '0deg');
        inner.style.setProperty('--ry', '0deg');
      });
    });
  }

  /* --------------------------------------------------------
     6. Case study expansion (Section 5a).
     The tile image grows from its exact grid rect into the
     panel (FLIP), then the copy assembles on a stagger.
     Closing reverses the same flight back to the tile.
     -------------------------------------------------------- */

  var overlay = document.getElementById('overlay');
  var panel = document.getElementById('panel');
  var panelImg = document.getElementById('panelImg');
  var panelDate = document.getElementById('panelDate');
  var panelTitle = document.getElementById('panelTitle');
  var panelProblem = document.getElementById('panelProblem');
  var panelStack = document.getElementById('panelStack');
  var panelBullets = document.getElementById('panelBullets');
  var panelClose = document.getElementById('panelClose');
  var overlayScrim = document.getElementById('overlayScrim');

  if (overlay && panel) {
    var EASE = 'cubic-bezier(0.16, 1, 0.3, 1)';
    var sheetQuery = window.matchMedia('(max-width: 760px)');
    var openTile = null;
    var lastFocus = null;
    var timers = [];
    var typeTimer = null;
    var flight = null;
    var isOpen = false;

    // backdrop blur is the first thing to go if the device is modest
    if ((navigator.hardwareConcurrency || 8) > 4 && !reduceMotion) {
      overlay.classList.add('has-blur');
    }

    function clearTimers() {
      timers.forEach(clearTimeout);
      timers = [];
      if (typeTimer) { clearInterval(typeTimer); typeTimer = null; }
    }

    function after(ms, fn) { timers.push(setTimeout(fn, ms)); }

    function lockScroll() {
      // pad out the scrollbar so hiding it does not shift the page
      var sb = window.innerWidth - document.documentElement.clientWidth;
      if (sb > 0) document.body.style.paddingRight = sb + 'px';
      document.body.classList.add('is-locked');
    }

    function unlockScroll() {
      document.body.classList.remove('is-locked');
      document.body.style.paddingRight = '';
    }

    /* --- fill the panel from the clicked tile --- */
    function populate(tile) {
      var img = tile.querySelector('.tile-inner img');
      var detail = tile.querySelector('.tile-detail');
      var heading = tile.querySelector('.caption h3');

      panelImg.src = img.getAttribute('src');
      panelImg.alt = img.getAttribute('alt') || '';
      panelTitle.textContent = heading ? heading.textContent.trim() : '';
      panelDate.textContent = detail.querySelector('.detail-date').textContent.trim();

      // the problem line is typed in later, so it starts empty
      panelProblem.textContent = '';
      panelProblem.dataset.line = detail.querySelector('.detail-problem').textContent.trim();

      panelStack.innerHTML = '';
      detail.querySelectorAll('.detail-stack li').forEach(function (src) {
        var chip = document.createElement('li');
        chip.textContent = src.textContent.trim();
        // a small random launch offset, so the chips do not march in as a row
        chip.style.setProperty('--cx', (Math.random() * 26 - 13).toFixed(0) + 'px');
        chip.style.setProperty('--cy', (10 + Math.random() * 14).toFixed(0) + 'px');
        panelStack.appendChild(chip);
      });

      panelBullets.innerHTML = '';
      detail.querySelectorAll('.detail-bullets li').forEach(function (src) {
        var li = document.createElement('li');
        li.innerHTML =
          '<svg class="bullet-mark" viewBox="0 0 14 14" aria-hidden="true">' +
          '<circle cx="7" cy="7" r="6"/></svg><span></span>';
        li.querySelector('span').textContent = src.textContent.trim();
        panelBullets.appendChild(li);
      });

      // reset every staged element for a fresh run
      [panelDate, panelTitle, panelProblem, panelStack, panelBullets].forEach(function (n) {
        n.classList.remove('is-in');
      });
      panel.querySelectorAll('.panel-problem-label, .panel-stack-label').forEach(function (n) {
        n.classList.remove('is-in');
      });
      panelProblem.classList.remove('is-typing');
    }

    /* --- the staged reveal, per spec 5a step 4 --- */
    function typeLine(el, text) {
      if (reduceMotion) { el.textContent = text; return; }
      var i = 0;
      el.classList.add('is-typing');
      typeTimer = setInterval(function () {
        el.textContent = text.slice(0, ++i);
        if (i >= text.length) {
          clearInterval(typeTimer);
          typeTimer = null;
          el.classList.remove('is-typing');
        }
      }, 16);
    }

    function runStagger() {
      var problemLabel = panel.querySelector('.panel-problem-label');
      var stackLabel = panel.querySelector('.panel-stack-label');

      panelDate.classList.add('is-in');
      panelTitle.classList.add('is-in');

      after(150, function () {
        problemLabel.classList.add('is-in');
        panelProblem.classList.add('is-in');
        typeLine(panelProblem, panelProblem.dataset.line || '');
      });

      after(300, function () {
        stackLabel.classList.add('is-in');
        panelStack.classList.add('is-in');
        panelStack.querySelectorAll('li').forEach(function (chip, i) {
          after(i * 40, function () { chip.classList.add('is-in'); });
        });
      });

      after(450, function () {
        panelBullets.classList.add('is-in');
        panelBullets.querySelectorAll('li').forEach(function (li, i) {
          after(i * 80, function () { li.classList.add('is-in'); });
        });
      });
    }

    /* --- open --- */
    function open(tile) {
      if (isOpen) return;
      isOpen = true;
      openTile = tile;
      lastFocus = document.activeElement;

      var first = tile.getBoundingClientRect();
      populate(tile);
      overlay.hidden = false;
      lockScroll();
      overlay.classList.add('is-open');

      var sheet = sheetQuery.matches;
      var frames;

      if (reduceMotion) {
        frames = null;
      } else if (sheet) {
        // touch viewports get a bottom sheet, not the shared-element flight
        frames = [{ transform: 'translateY(100%)' }, { transform: 'none' }];
      } else {
        var last = panel.getBoundingClientRect();
        frames = [{
          transform: 'translate(' + (first.left - last.left) + 'px,' + (first.top - last.top) + 'px)' +
                     ' scale(' + (first.width / last.width) + ',' + (first.height / last.height) + ')',
          opacity: 0.55
        }, {
          transform: 'none',
          opacity: 1
        }];
      }

      panelClose.focus();

      if (!frames) { runStagger(); return; }

      flight = panel.animate(frames, {
        duration: sheet ? 420 : 560,
        easing: EASE,
        fill: 'both'
      });
      flight.finished.then(function () {
        if (flight) flight.cancel();   // final frame equals the resting style
        flight = null;
        runStagger();
      }).catch(function () { /* superseded by a close */ });
    }

    /* --- close: the image visibly returns home --- */
    function close() {
      if (!isOpen) return;
      isOpen = false;
      clearTimers();
      if (flight) { flight.cancel(); flight = null; }

      var done = function () {
        overlay.hidden = true;
        overlay.classList.remove('is-open');
        unlockScroll();
        if (lastFocus && lastFocus.focus) lastFocus.focus();
        openTile = null;
      };

      if (reduceMotion || !openTile) { done(); return; }

      var last = panel.getBoundingClientRect();
      var first = openTile.getBoundingClientRect();
      var frames = sheetQuery.matches
        ? [{ transform: 'none' }, { transform: 'translateY(100%)' }]
        : [{ transform: 'none', opacity: 1 }, {
            transform: 'translate(' + (first.left - last.left) + 'px,' + (first.top - last.top) + 'px)' +
                       ' scale(' + (first.width / last.width) + ',' + (first.height / last.height) + ')',
            opacity: 0.55
          }];

      overlay.classList.remove('is-open');
      var back = panel.animate(frames, { duration: 420, easing: EASE, fill: 'both' });
      back.finished.then(function () { back.cancel(); done(); }).catch(done);
    }

    tiles.forEach(function (tile) {
      var hit = tile.querySelector('.tile-hit');
      if (hit) hit.addEventListener('click', function () { open(tile); });
    });

    panelClose.addEventListener('click', close);
    overlayScrim.addEventListener('click', close);

    document.addEventListener('keydown', function (e) {
      if (!isOpen) return;
      if (e.key === 'Escape') { close(); return; }
      if (e.key !== 'Tab') return;

      // keep focus inside the dialog while it is open
      var focusables = panel.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (!focusables.length) return;
      var firstEl = focusables[0];
      var lastEl = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    });
  }
})();
