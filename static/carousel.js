/* Home carousel: vanilla JS, no deps. Autoplay 5s; pauses on hover/focus/touch; arrows, dots, keyboard, swipe; no autoplay with prefers-reduced-motion. */
(function () {
  var _L = window.RECARCH_L10N || {}; function L(k, d, o) { var s = _L[k] != null ? _L[k] : d; return o ? s.replace(/\{(\w+)\}/g, function (m, x) { return o[x]; }) : s; }
  var root = document.querySelector(".carousel");
  if (!root) return;
  var track = root.querySelector(".car-track"), slides = [].slice.call(root.querySelectorAll(".slide")), dots = [].slice.call(root.querySelectorAll(".dot"));
  var n = slides.length; if (n < 2) { [].forEach.call(root.querySelectorAll(".car-btn,.car-foot"), function (e) { e.hidden = true; }); }
  var delay = parseInt(root.getAttribute("data-autoplay"), 10) || 5000, cur = 0, timer = null, hold = { hover: false, focus: false, touch: false, user: false }, pointerFocus = false;
  var reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var pauseBtn = root.querySelector(".car-pause");

  // relative dates stay correct even if the page is older than the build
  function rel(d) {
    var a = new Date(d + "T00:00:00"), b = new Date(); b.setHours(0, 0, 0, 0);
    var k = Math.round((b - a) / 864e5); return k <= 0 ? L("today", "today") : k === 1 ? L("yesterday", "yesterday") : L("days_ago", "{n} days ago", { n: k });
  }
  [].forEach.call(root.querySelectorAll("time[data-date]"), function (t) { t.textContent = rel(t.getAttribute("data-date")); });

  function show(i, fromUser) {
    cur = (i + n) % n;
    track.style.transform = "translateX(" + (-100 * cur) + "%)";
    slides.forEach(function (s, k) {
      var on = k === cur; s.setAttribute("aria-hidden", on ? "false" : "true");
      [].forEach.call(s.querySelectorAll("a"), function (a) { if (on) a.removeAttribute("tabindex"); else a.setAttribute("tabindex", "-1"); });
    });
    dots.forEach(function (d, k) { d.setAttribute("aria-current", k === cur ? "true" : "false"); });
    if (fromUser) restart();
  }
  function paused() { return hold.hover || hold.focus || hold.touch || hold.user; }
  function tick() { if (!paused()) show(cur + 1); }
  function restart() { stop(); if (!reduced && n > 1) timer = setInterval(tick, delay); }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }

  root.querySelector(".car-prev").addEventListener("click", function () { show(cur - 1, true); });
  root.querySelector(".car-next").addEventListener("click", function () { show(cur + 1, true); });
  dots.forEach(function (d) { d.addEventListener("click", function () { show(parseInt(d.getAttribute("data-go"), 10), true); }); });
  root.addEventListener("mouseenter", function () { hold.hover = true; });
  root.addEventListener("mouseleave", function () { hold.hover = false; });
  // Focus pauses autoplay only when it came from the keyboard. A click on an arrow or dot leaves focus on that button, which must not hold the
  // carousel for ever: after a pointer interaction it resumes once the pointer leaves. A keyboard user stays paused until focus leaves the carousel.
  root.addEventListener("mousedown", function () { pointerFocus = true; });
  root.addEventListener("focusin", function () { hold.focus = !pointerFocus; });
  root.addEventListener("focusout", function () { hold.focus = false; pointerFocus = false; });
  root.addEventListener("keydown", function (e) {
    pointerFocus = false; hold.focus = true;
    if (e.key === "ArrowLeft") { show(cur - 1, true); e.preventDefault(); }
    else if (e.key === "ArrowRight") { show(cur + 1, true); e.preventDefault(); }
  });
  var x0 = null, y0 = null;
  root.addEventListener("touchstart", function (e) { hold.touch = true; pointerFocus = true; var t = e.touches[0]; x0 = t.clientX; y0 = t.clientY; }, { passive: true });
  root.addEventListener("touchend", function (e) {
    hold.touch = false; var t = e.changedTouches[0];
    if (x0 !== null) { var dx = t.clientX - x0, dy = t.clientY - y0; if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) show(cur + (dx < 0 ? 1 : -1), true); }
    x0 = null;
  });
  root.addEventListener("touchcancel", function () { hold.touch = false; x0 = null; });
  if (pauseBtn) {
    if (reduced || n < 2) pauseBtn.hidden = true;
    pauseBtn.addEventListener("click", function () {
      hold.user = !hold.user; pauseBtn.setAttribute("aria-pressed", hold.user ? "true" : "false"); pauseBtn.textContent = hold.user ? L("play", "Play") : L("pause", "Pause");
    });
  }
  root.setAttribute("data-autoplaying", reduced ? "false" : "true");
  show(0); restart();
})();
