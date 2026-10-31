/* Newsletter: loads the Beehiiv form only when the reader opens the "subscribe here" disclosure.
   Without JS the section keeps its button to the hosted subscribe page; this script reveals the disclosure. */
(function () {
  var boxes = document.querySelectorAll('details.nl-inline');
  Array.prototype.forEach.call(boxes, function (d) {
    d.hidden = false;
    d.addEventListener('toggle', function () {
      if (!d.open || d.getAttribute('data-loaded')) return;
      d.setAttribute('data-loaded', '1');
      var host = d.querySelector('.nl-embed');
      var s = document.createElement('script');
      s.async = true; s.src = d.getAttribute('data-loader'); s.setAttribute('data-beehiiv-form', d.getAttribute('data-form'));
      host.appendChild(s);
      var a = document.createElement('script');
      a.async = true; a.src = d.getAttribute('data-attr');
      document.body.appendChild(a);
      var title = d.getAttribute('data-title');
      function label() { var f = host.querySelector('iframe'); if (f && !f.title) f.title = title; return !!(f && f.title); }
      if (!label() && window.MutationObserver) {
        var mo = new MutationObserver(function () { if (label()) mo.disconnect(); });
        mo.observe(host, { childList: true, subtree: true });
        setTimeout(function () { mo.disconnect(); }, 20000);
      }
    });
  });
})();
