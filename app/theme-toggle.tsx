"use client";

import { useLayoutEffect, useSyncExternalStore } from "react";

const STORAGE_KEY = "theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

// The active theme is a stored choice on <html data-theme>, else the system preference.
function isDark() {
  const theme = document.documentElement.dataset.theme;
  return theme ? theme === "dark" : window.matchMedia(DARK_QUERY).matches;
}

function subscribe(onChange: () => void) {
  const media = window.matchMedia(DARK_QUERY);
  media.addEventListener("change", onChange);
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => {
    media.removeEventListener("change", onChange);
    observer.disconnect();
  };
}

function readStored() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function ThemeToggle() {
  // null on the server and during hydration: the button stays hidden until it has mounted.
  const dark = useSyncExternalStore(subscribe, isDark, () => null);

  // React's dev remount resets <html> attributes, dropping what the head script set.
  // In production this re-applies the same value and changes nothing.
  useLayoutEffect(() => {
    const stored = readStored();
    if (stored === "dark" || stored === "light") document.documentElement.dataset.theme = stored;
  }, []);

  function toggle() {
    const next = isDark() ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage blocked: the choice lasts for this page view only.
    }
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      aria-label="Theme: dark mode"
      aria-pressed={dark ?? false}
      hidden={dark === null}
      onClick={toggle}
    >
      <span aria-hidden="true">◐</span>
      Theme
    </button>
  );
}
