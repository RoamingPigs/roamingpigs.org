/* RoamingPigs Research Notes: small progressive enhancements. The site works without this file. */
(function () {
  "use strict";

  // Copy buttons stay hidden until the clipboard path is known to exist.
  var buttons = document.querySelectorAll("button.copy[data-copy]");
  buttons.forEach(function (btn) {
    var target = document.getElementById(btn.getAttribute("data-copy"));
    if (!target) return;
    btn.hidden = false;
    btn.addEventListener("click", function () {
      var text = target.innerText;
      var done = function () {
        var old = btn.textContent;
        btn.textContent = "Copied";
        setTimeout(function () { btn.textContent = old; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
      } else {
        fallback(text, done);
      }
    });
  });

  function fallback(text, done) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.className = "sr-only";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); done(); } catch (e) { /* leave the text selectable */ }
    document.body.removeChild(ta);
  }

  // Mobile menu: close on Escape and after choosing a link.
  var menu = document.querySelector("details.nav-toggle");
  if (menu) {
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && menu.open) { menu.open = false; menu.querySelector("summary").focus(); }
    });
    menu.addEventListener("click", function (e) {
      if (e.target.closest("a")) menu.open = false;
    });
  }
})();
