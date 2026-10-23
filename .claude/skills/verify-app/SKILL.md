---
name: verify-app
description: Launch, check, drive and screenshot the About Me static site (index.html served by python3 http.server) and collect evidence. Use whenever a change touches index.html, styles.css or any asset, to prove the page still renders with the approved content, links and keyboard access — before finishing a ticket, or when asked to "verify", "run the app", "screenshot the page" or "check it works".
---

# verify-app

The site is one static page (`index.html` + `styles.css` + `theme.js`) with no build step, published under
the GitHub Pages sub-path `/about-me/`. This skill serves the repo exactly as Pages would serve
it, checks it, drives it in headless Chrome and keeps the evidence.

One command runs the whole loop and always cleans up after itself:

```sh
.claude/skills/verify-app/scripts/run.sh all
```

Exit 0 means every step passed. Each phase can also run alone:
`run.sh launch | doctor | drive | cleanup` (run `cleanup` yourself after a manual `launch`).

## Launch

- From the repo root: `python3 -m http.server 8765 --bind 127.0.0.1` in the background.
  The PID goes to `.fredrin/tmp/verify-app.pid`, the port to `.fredrin/tmp/verify-app.port`,
  server output to `.fredrin/tmp/verify-app.server.log`.
- **Ready means usable**, not "process started": it polls
  `curl -sf http://127.0.0.1:<port>/ | grep -q 'Ayoub Lkebch'` every 0.5s for at most 10s.
- If port 8765 is already listening, it takes the next free port and prints
  `NOTE  port 8765 is busy — using <port> instead`. It never touches whatever holds 8765.

## Doctor (read-only)

`python3 .claude/skills/verify-app/scripts/doctor.py .` checks:

- `python3` is present and `index.html` exists.
- Every local `href`/`src` in `index.html` resolves to a file in the repo.
- No root-absolute local paths (`href="/…"`, `src="/…"`) — they would break under `/about-me/`.
- No positive `tabindex` (so keyboard order is document order).
- SEO/social metadata: description, theme-color, the `og:*` and `twitter:*` tags, and
  `canonical`/`icon`/`apple-touch-icon` links are present; `canonical` and `og:url` both equal
  `https://itsandl.github.io/about-me/` (lowercase); `og:image`/`twitter:image` are that base +
  `og-image.png`; `favicon.svg`, `favicon.ico`, `apple-touch-icon.png`, `og-image.png`,
  `robots.txt` and `sitemap.xml` exist; `og-image.png` is 1200×630; the JSON-LD `Person` parses.
- HTML is well-formed: a local `html.parser` pass that reports unclosed and stray tags, **and**
  the W3C Nu checker when reachable
  (`curl -s -H 'Content-Type: text/html; charset=utf-8' --data-binary @index.html 'https://validator.w3.org/nu/?out=json'`).
  Offline it prints `SKIP  W3C Nu checker unreachable` and relies on the local pass.

## Drive

Chrome: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`, else `google-chrome` /
`chromium` / `chromium-browser` on PATH. Against `http://127.0.0.1:<port>/` it:

1. Saves the served HTML (`curl`) and the rendered DOM (`--dump-dom`, light and dark).
2. Screenshots desktop at `--window-size=1280,1400`, light and dark.
3. Screenshots the phone view at 390px wide, light and dark. Headless Chrome will not size a
   window below ~500px, so `scripts/cdp.mjs phone` (node 22+) emulates a real 390px mobile viewport
   over the DevTools protocol and captures the full page. Without node 22+ it falls back to loading
   the page in a 390px `<iframe>` (wrapper written to `.fredrin/tmp/verify-app-frame/phone.html`)
   inside a 500px window — the right 110px of those images is wrapper background.
   The phone run also asserts `document.documentElement.scrollWidth <= 390` (no sideways scroll).
4. Asserts content with `scripts/check_content.py dom.html` — every feature in the map below,
   plus all 9 external/mailto URLs in order and their `target`/`rel`.
5. Presses a real **Tab** key once (`scripts/cdp.mjs tab`) and asserts focus lands on a visible
   `Skip to content` link to `#main`; saves `keyboard-first-tab.png` of the focused state.
   Without node 22+ this is reported as NOT VERIFIED — say so; the run is not keyboard-checked.
6. Clicks the theme toggle and reloads (`scripts/cdp.mjs theme`), then loads the page with
   JavaScript disabled under a dark system theme (`scripts/cdp.mjs nojs`) — see
   `features/theme.md`. Results go to `theme-check.txt`; NOT VERIFIED without node 22+.

Every Chrome call has a watchdog (60s per CLI call, 30s per `cdp.mjs` run) so a hung browser
fails the run instead of hanging it, and every expected screenshot/DOM file must exist and be
non-empty or Drive fails.

**Dark mode:** both `--force-dark-mode` and `--blink-settings=preferredColorScheme=0` make
`prefers-color-scheme: dark` match in headless Chrome (checked on Chrome for macOS);
the runner uses `--force-dark-mode`. `cdp.mjs` uses `Emulation.setEmulatedMedia`.
A page-level toggle (`data-theme`) is not a media query — drive it per `features/theme.md`.
To screenshot the pinned dark theme by hand, run `cdp.mjs theme` (it saves `theme-toggle.png`
after the reload), or set `localStorage.theme = "dark"` over CDP and reload.

**No Chrome:** Drive prints `SKIP  no Chrome/Chromium found`, asserts on the served HTML with
`check_content.py`, and takes no screenshots. Say so plainly — that is not a visual check.

## Evidence

Everything lands in `.fredrin/tmp/verify-app/<YYYYmmdd-HHMMSS>/` (git-ignored):

| File | What |
|---|---|
| `SUMMARY.md` | action taken, resulting state (e.g. ".project × 4, .contact-link × 4"), side effects |
| `desktop-{light,dark}.png`, `phone-{light,dark}.png` | screenshots |
| `keyboard-first-tab.{png,json}` | focused element after the first Tab |
| `theme-toggle.{png,json}` | state before the click, after it, and after the reload |
| `nojs-dark.{png,json}` | full render with JavaScript disabled, dark system theme |
| `served.html`, `dom.html`, `dom-dark.html` | what the server sent / what Chrome rendered |
| `content-check.txt`, `phone-check.txt`, `keyboard-check.txt`, `theme-check.txt` | PASS/FAIL lines |

Side effects: none expected — static site, nothing written outside `.fredrin/tmp/`. The only
outbound request is Doctor's optional POST of `index.html` to the W3C checker.

To attach to a ticket: `./.fredrin/fredrin ticket upload <png> --kind after --pair <screen-slug>`.

## Cleanup

Kills **only** the PID in `.fredrin/tmp/verify-app.pid`, then removes the pid/port files.
It never kills other processes on the port. The evidence folder is kept.
Before killing, it confirms that PID is still an `http.server` (a stale pid file can point at a
reused PID). Confirm nothing is left: `pgrep -f 'http.server'` prints nothing.

A second `launch` while one is live refuses ("already launched — run cleanup first") instead of
starting a second server the pid file would lose track of.

## Feature map

One file per feature under `features/` — selectors, expected content and the check command:

- `features/intro.md` — header monogram, name, lede, AI note, location
- `features/projects.md` — the "Shipped" list
- `features/contact.md` — the four contact links
- `features/footer.md` — copyright line and source link
- `features/theme.md` — light/dark theme, the toggle and the no-flash script

When a change adds a feature, add its file
here and its assertions to `check_content.py` (or a new script the runner calls).
