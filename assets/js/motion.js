/* Reveal-on-scroll for cards, figures and sections. Does nothing if the browser
   lacks IntersectionObserver or the reader prefers reduced motion. */
(function () {
  if (!('IntersectionObserver' in window)) return;
  if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var sel = [
    '.card', '.program', '.project', '.pubpanel', '.contact-card', '.notice', '.statline',
    '.prose > h2', '.prose > figure', '.prose .textfig', '.prose .explain', '.gallery figure',
    'details.topic', '.topic-group', '.people li', '.group h2', '.section-label', '.home-figure', '.programs-text li'
  ].join(',');
  var els = Array.prototype.slice.call(document.querySelectorAll(sel));
  var vh = window.innerHeight || 800;
  document.documentElement.classList.add('js');
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -6% 0px', threshold: 0.06 });
  // anything already scrolled past (fast scrolling, jumping to an anchor) is shown too
  var pending = false;
  function sweep() {
    pending = false;
    var bottom = window.innerHeight || vh;
    els.forEach(function (el) { if (!el.classList.contains('in') && el.getBoundingClientRect().top < bottom) { el.classList.add('in'); io.unobserve(el); } });
  }
  window.addEventListener('scroll', function () { if (!pending) { pending = true; requestAnimationFrame(sweep); } }, { passive: true });
  window.addEventListener('beforeprint', function () { els.forEach(function (el) { el.classList.add('in'); }); });
  els.forEach(function (el, i) {
    // things already on screen appear at once, with a small stagger
    var r = el.getBoundingClientRect();
    el.classList.add('reveal');
    if (r.top < vh) { el.style.transitionDelay = Math.min(i, 8) * 45 + 'ms'; requestAnimationFrame(function () { el.classList.add('in'); }); }
    else io.observe(el);
  });
})();
