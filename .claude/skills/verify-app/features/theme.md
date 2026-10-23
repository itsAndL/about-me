# Feature: theme (light/dark toggle)

Light/dark tokens on `:root` in `app/globals.css`; the toggle is `app/theme-toggle.tsx` (the only
client component), mounted in `header.site-header`; the no-flash head script is in `app/layout.tsx`.

## Contract

| State | `<html data-theme>` | `button.theme-toggle` |
|---|---|---|
| No stored choice | absent — CSS follows `prefers-color-scheme` (live) | `aria-pressed` = system is dark |
| After a click | `dark` / `light`, also saved to `localStorage.theme` | `aria-pressed="true"` when dark |
| Reload with a stored choice | set by the `<head>` script before first paint | same as before the reload |
| JS off | absent — system theme via the media query | in the HTML with `hidden`, so not shown |
| Storage blocked | set for the page view only | works, nothing persists |

- Accessible name `Theme: dark mode` (starts with the visible text "Theme", WCAG 2.5.3); the
  `◐` glyph is `aria-hidden`. Toggle state is `aria-pressed`.
- `<html>` carries `suppressHydrationWarning` (the head script changes it before React hydrates).
  No other element suppresses hydration warnings.
- Dark backgrounds: `--bg` `#111312` = `rgb(17, 19, 18)`; light `#fbfaf7` = `rgb(251, 250, 247)`.

## Check

`run.sh all` runs it (Drive step). Alone, against a launched server:

```sh
node .claude/skills/verify-app/scripts/cdp.mjs theme "<chrome>" http://127.0.0.1:<port>/about-me/ <evidence-dir>
```

It clears `localStorage.theme`, loads with system light, then:

1. waits for the toggle to unhide (hydration) and checks no `data-theme`, `aria-pressed="false"`;
2. clicks the button with a real mouse event → `data-theme="dark"`, `aria-pressed="true"`,
   `localStorage.theme="dark"` (`theme-after-click.png`);
3. reloads with `*/_next/static/*.js*` blocked, so only the inline head script runs →
   `data-theme="dark"` and the dark background (the no-flash proof);
4. reloads normally → `data-theme="dark"`, `aria-pressed="true"` (`theme-after-reload.png`), and
   no console message or uncaught exception (CDP `Runtime` + `Log`) matches `/hydrat/i` or the
   minified React hydration errors `#418/#419/#423–#425`;
5. at a 390px mobile viewport, once hydrated, `document.documentElement.scrollWidth <= 390`;
6. with script execution disabled (system light, then dark): 4 `.project`s, the system
   background, toggle not visible (`theme-js-off-{light,dark}.png`).

Results: `theme-check.txt` (PASS/FAIL lines) and `theme-check.json`.

Screenshots of the dark theme come from the system preference (`--force-dark-mode`,
`Emulation.setEmulatedMedia`); `theme-after-click.png` is the toggle-driven dark render.
