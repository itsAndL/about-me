# Feature: contact

`section.contact[aria-labelledby="contact-heading"]` with `<h2 id="contact-heading">Contact</h2>`
and a `<ul>` of four `a.contact-link`, in this order.

## Selectors

| # | `a.contact-link` href | Text | Opens |
|---|---|---|---|
| 1 | `mailto:ayoub003lkebch@gmail.com` | `ayoub003lkebch@gmail.com` | same tab (no `target`) |
| 2 | `https://www.linkedin.com/in/ayoublkebch` | `LinkedIn` | new tab |
| 3 | `https://github.com/itsAndL` | `GitHub` | new tab |
| 4 | `https://ayoublkebch.com` | `ayoublkebch.com` | new tab |

The email and website links hold two labels: `<span class="label-long">` (the full value,
shown above 520px) and `<span class="label-short">` (`Email` / `Website`, shown at ≤520px, where
the links form an even 2×2 grid). Each of those two links has an `aria-label` with the full value
(`Email ayoub003lkebch@gmail.com`, `Website ayoublkebch.com (opens in a new tab)`).

New-tab links carry `target="_blank" rel="noopener noreferrer"` and a visually hidden
" (opens in a new tab)".

## Check

```sh
python3 .claude/skills/verify-app/scripts/check_content.py <evidence>/dom.html contact
```
