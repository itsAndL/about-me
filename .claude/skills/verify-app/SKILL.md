---
name: verify-app
description: Build, launch, check, drive and screenshot the About Me site (Next.js 16 static export, served under /about-me/ by python3 http.server) and collect evidence. Use whenever a change touches app/, public/, next.config.ts, package.json or the Pages workflow, to prove the exported page still renders with the approved content, links, base-path assets and keyboard access — before finishing a ticket, or when asked to "verify", "run the app", "screenshot the page" or "check it works".
---

# verify-app

The site is a Next.js 16 + TypeScript App Router app exported statically (`output: "export"`,
`basePath: "/about-me"`, `trailingSlash: true` in `next.config.ts`). `npm run build` writes it to
`out/`, and GitHub Pages serves that folder at `https://itsandl.github.io/about-me/`. This skill
builds the export, serves it under `/about-me/` exactly as Pages does, checks it, drives it in
headless Chrome and keeps the evidence.

One command runs the whole loop and always cleans up after itself:

```sh
.claude/skills/verify-app/scripts/run.sh all
```

Exit 0 means every step passed. Each phase can also run alone:
`run.sh build | launch | doctor | drive | cleanup` (run `cleanup` yourself after a manual `launch`).

For quick iteration while editing, `npm run dev` serves the app with hot reload at
http://localhost:3000/about-me/ (the base path applies in dev too). It is not what Pages serves —
always finish with `run.sh all`.

## Build

1. `npm ci` when `node_modules/` is missing or older than `package-lock.json`, then `npm run build` (log:
   `.fredrin/tmp/verify-app.build.log`). Fails if `out/index.html` is missing afterwards.
2. Copies `out/` to `.fredrin/tmp/site/about-me/`, so serving `.fredrin/tmp/site/` mirrors the
   Pages sub-path: root-absolute `/…` URLs that forgot the base path 404 here just as they do live.

## Launch

- `python3 -m http.server 8765 --bind 127.0.0.1` from `.fredrin/tmp/site/`, in the background.
  The PID goes to `.fredrin/tmp/verify-app.pid`, the port to `.fredrin/tmp/verify-app.port`,
  server output to `.fredrin/tmp/verify-app.server.log`.
- **Ready means usable**, not "process started": it polls
  `curl -sf http://127.0.0.1:<port>/about-me/ | grep -q 'Ayoub Lkebch'` every 0.5s for at most 10s.
- If port 8765 is already listening, it takes the next free port and prints
  `NOTE  port 8765 is busy — using <port> instead`. It never touches whatever holds 8765.

## Doctor (read-only)

`python3 .claude/skills/verify-app/scripts/doctor.py . [--served http://127.0.0.1:<port>]` checks:

- node ≥ 20.9 and npm are present; `npx tsc --noEmit` and `npm run lint` pass.
- `out/index.html` exists (run the build first).
- Every local `href`/`src` in `out/index.html` starts with `/about-me/` and resolves to a file in
  `out/`, and the page holds zero root-absolute `/_next/…` references (attributes or inline
  scripts) — those would break under the sub-path.
- With `--served` (what `run.sh` passes once launched): every one of those assets returns 200
  from the local server.
- The assets moved into `public/` (`.nojekyll`, favicons, `og-image.png`, `robots.txt`,
  `sitemap.xml`) ship in `out/`.
- No positive `tabindex` (so keyboard order is document order).
- HTML is well-formed: a local `html.parser` pass, **and** the W3C Nu checker when reachable.
  Offline it prints `SKIP  W3C Nu checker unreachable` and relies on the local pass.

## Drive

Chrome: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`, else `google-chrome` /
`chromium` / `chromium-browser` on PATH. Against `http://127.0.0.1:<port>/about-me/` it:

1. Saves the served HTML (`curl`) and the rendered DOM (`--dump-dom`, light and dark).
2. Screenshots desktop at `--window-size=1280,1400`, light and dark.
3. Screenshots the phone view at 390px wide, light and dark. Headless Chrome will not size a
   window below ~500px, so `scripts/cdp.mjs phone` (node 22+) emulates a real 390px mobile viewport
   over the DevTools protocol and captures the full page. Without node 22+ it falls back to loading
   the page in a 390px `<iframe>` (wrapper served from `.fredrin/tmp/site/verify-app-frame/phone.html`)
   inside a 500px window — the right 110px of those images is wrapper background.
4. Asserts content with `scripts/check_content.py dom.html` — every feature in the map below,
   plus all 9 external/mailto URLs in order and their `target`/`rel`. It also works on the raw
   export: `check_content.py out/index.html`.
5. Presses a real **Tab** key once (`scripts/cdp.mjs tab`) and asserts focus lands on a visible
   `Skip to content` link to `#main`; saves `keyboard-first-tab.png` of the focused state.
   Without node 22+ this is reported as NOT VERIFIED — say so; the run is not keyboard-checked.
6. Drives the theme toggle (`scripts/cdp.mjs theme`, see `features/theme.md`): click → reload
   persistence, `aria-pressed`, `localStorage`, no hydration warnings, 390px scroll width and a
   JS-off load in both system themes. Also NOT VERIFIED without node 22+.

The phone screenshots wait (up to 5s) for the theme toggle to unhide, i.e. for React to hydrate.

Every Chrome call has a watchdog (60s per CLI call, 30s per `cdp.mjs` run) so a hung browser
fails the run instead of hanging it, and every expected screenshot/DOM file must exist and be
non-empty or Drive fails.

**Next.js markup notes:** Next injects a `<div hidden>` (streamed-metadata boundary) as the first
child of `<body>`; the "skip link is first" check ignores `hidden` elements. React escapes `'` as
`&#x27;` in the exported HTML, so `check_content.py` compares strings after unescaping. Adjacent
JSX text expressions render a `<!-- -->` separator — keep each verbatim string one text node.

**Dark mode:** both `--force-dark-mode` and `--blink-settings=preferredColorScheme=0` make
`prefers-color-scheme: dark` match in headless Chrome (checked on Chrome for macOS);
the runner uses `--force-dark-mode`. `cdp.mjs` uses `Emulation.setEmulatedMedia`.
A page-level toggle (`data-theme`) is not a media query — `cdp.mjs theme` drives it per
`features/theme.md` (click, reload, JS off).

**No Chrome:** Drive prints `SKIP  no Chrome/Chromium found`, asserts on the served HTML with
`check_content.py`, and takes no screenshots. Say so plainly — that is not a visual check.

## Evidence

Everything lands in `.fredrin/tmp/verify-app/<YYYYmmdd-HHMMSS>/` (git-ignored):

| File | What |
|---|---|
| `SUMMARY.md` | action taken, resulting state (e.g. ".project × 4, .contact-link × 4"), side effects |
| `desktop-{light,dark}.png`, `phone-{light,dark}.png` | screenshots |
| `keyboard-first-tab.{png,json}` | focused element after the first Tab |
| `theme-check.{txt,json}`, `theme-*.png` | theme toggle drive: after click, after reload, JS off light/dark |
| `served.html`, `dom.html`, `dom-dark.html` | what the server sent / what Chrome rendered |
| `content-check.txt`, `keyboard-check.txt` | PASS/FAIL lines |

Side effects: `out/` is rebuilt and staged into `.fredrin/tmp/site/about-me/`; nothing else is
written outside `.fredrin/tmp/`. The only outbound request is Doctor's optional POST of
`out/index.html` to the W3C checker.

To attach to a ticket: `./.fredrin/fredrin ticket upload <png> --kind after --pair <screen-slug>`.

## Cleanup

Kills **only** the PID in `.fredrin/tmp/verify-app.pid`, then removes the pid/port files.
It never kills other processes on the port. The evidence folder is kept.
Before killing, it confirms that PID is still an `http.server` (a stale pid file can point at a
reused PID). Confirm nothing is left: `pgrep -f 'http.server'` prints nothing.

A second `launch` (or `all`) while one is live refuses ("already launched — run cleanup first")
instead of starting a second server the pid file would lose track of.

## Deploy

Pushes to `main` run `.github/workflows/pages.yml`: `npm ci` → `npm run build` → upload `out/` →
deploy. After a deploy finishes, check the live site:

```sh
curl -sf https://itsandl.github.io/about-me/ | grep -q 'Ayoub Lkebch'
asset=$(curl -sf https://itsandl.github.io/about-me/ | grep -oE '/about-me/_next/[^"]+\.css' | head -1)
curl -s -o /dev/null -w '%{http_code}\n' "https://itsandl.github.io$asset"   # expect 200
```

## Feature map

One file per feature under `features/` — selectors, expected content, source and check command.
The copy lives in `app/content.ts` (projects, contact links) and `app/page.tsx` (intro, footer):

- `features/intro.md` — skip link, header monogram, name, lede, AI note, location
- `features/projects.md` — the "Shipped" list
- `features/contact.md` — the four contact links
- `features/footer.md` — copyright line and source link
- `features/theme.md` — light/dark tokens, the theme toggle and the no-flash head script

When a change adds a feature, add its file here and its assertions to `check_content.py`
(or a new script the runner calls).
