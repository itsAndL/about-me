// Theme toggle: shown only with JS. The inline <head> script applies a saved choice before paint.
(function () {
  var root = document.documentElement;
  var button = document.querySelector(".theme-toggle");
  var system = window.matchMedia("(prefers-color-scheme: dark)");
  if (!button) return;

  function isDark() {
    var chosen = root.getAttribute("data-theme");
    return chosen ? chosen === "dark" : system.matches;
  }

  function sync() {
    button.setAttribute("aria-pressed", String(isDark()));
  }

  button.addEventListener("click", function () {
    var next = isDark() ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch (e) {
      // Storage blocked: the choice lasts for this page view only.
    }
    sync();
  });

  if (system.addEventListener) system.addEventListener("change", sync);
  else if (system.addListener) system.addListener(sync);
  sync();
  button.hidden = false;
})();
