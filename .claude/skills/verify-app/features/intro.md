# Feature: intro

Header and introduction at the top of the page. Source: skip link in `app/layout.tsx`, the
rest in `app/page.tsx`.

## Selectors

| Selector | Expected |
|---|---|
| `a.visually-hidden-focusable` (first visible element in `body`; Next's `<div hidden>` precedes it) | `Skip to content`, `href="#main"`; hidden until focused |
| `header.site-header .monogram` | `AL` — plain text, not a link (the styling ticket adds the theme toggle beside it) |
| `main#main .intro h1` | `Ayoub Lkebch` |
| `.intro .lede` | `Full-stack product engineer. I build software for businesses — <strong>4 B2B products shipped</strong>, now building <strong>Opilote</strong>.` |
| `.intro .ai-note` | `I work with AI coding agents every day: I write the spec, review every diff, and ship small PRs.` |
| `.intro .location` | `Casablanca, Morocco` |

## Check

```sh
python3 .claude/skills/verify-app/scripts/check_content.py <evidence>/dom.html intro
node .claude/skills/verify-app/scripts/cdp.mjs tab "<chrome>" http://127.0.0.1:8765/about-me/ <evidence>   # skip link on first Tab
```
