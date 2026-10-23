# Feature: footer

Source: `app/page.tsx` (the source URL is `sourceUrl` in `app/content.ts`).

## Selectors

| Selector | Expected |
|---|---|
| `footer.site-footer p` | `© 2026 Ayoub Lkebch · Built with Fredrin · ` followed by the source link |
| `footer.site-footer a` | `https://github.com/itsAndL/about-me`, text `Source on GitHub`, `target="_blank" rel="noopener noreferrer"` |

## Check

```sh
python3 .claude/skills/verify-app/scripts/check_content.py <evidence>/dom.html footer
```

Running `check_content.py <dom>` with no feature names checks every feature and also asserts
that all 9 external/mailto URLs on the page match the approved list, in order.
