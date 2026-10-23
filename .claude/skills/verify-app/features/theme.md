# Feature: theme

Light/dark theme. The system preference (`prefers-color-scheme`) is the default; a toggle in
the header pins a choice in `localStorage['theme']`.

## Selectors

| What | Where | Expected |
|---|---|---|
| Toggle | `header.site-header > button.theme-toggle[type="button"]` | ships with `hidden`; `theme.js` removes it. Shows `◐` (`aria-hidden`) + "Theme"; `aria-label="Dark mode theme"` |
| Pressed state | `button.theme-toggle[aria-pressed]` | `"true"` when the active theme is dark (pinned or from the system), else `"false"` |
| Pinned theme | `<html data-theme="light\|dark">` | absent until the toggle is clicked or a saved choice is restored |
| Saved choice | `localStorage['theme']` | `"light"` or `"dark"`; blocked storage → choice lasts for the page view only |
| No-flash script | inline `<script>` in `<head>`, **before** `<link rel="stylesheet">` | copies `localStorage['theme']` onto `data-theme` before first paint |
| Background | `getComputedStyle(body).backgroundColor` | light `rgb(251, 250, 247)`, dark `rgb(17, 19, 18)` |

With JS off the toggle stays hidden and the page follows the system theme.

## Check

```sh
node .claude/skills/verify-app/scripts/cdp.mjs theme "<chrome>" http://127.0.0.1:<port>/ <evidence>
node .claude/skills/verify-app/scripts/cdp.mjs nojs  "<chrome>" http://127.0.0.1:<port>/ <evidence>
```

`theme` emulates a light system theme, clicks the toggle with a real mouse event, reloads and
asserts `data-theme="dark"`, `aria-pressed="true"`, `localStorage['theme'] === "dark"`, a dark
body background, and that `data-theme` was already `dark` when the stylesheet `<link>` was
parsed — i.e. set before any styled paint, which is what rules out a light flash. Writes `theme-toggle.{png,json}`.

`nojs` disables JavaScript over the DevTools protocol (`Emulation.setScriptExecutionDisabled`),
emulates a dark system theme and asserts the toggle is hidden, no `data-theme` is set, the body
is dark and all projects and contact links rendered. Writes `nojs-dark.{png,json}`.
`--blink-settings=scriptEnabled=false` is not used: headless Chrome's `--screenshot` and
`--dump-dom` produce nothing with it.

`run.sh drive` runs both and writes their PASS/FAIL lines to `theme-check.txt`.
