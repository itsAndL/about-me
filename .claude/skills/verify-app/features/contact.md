# Feature: contact

`section.contact[aria-labelledby="contact-heading"]` with `<h2 id="contact-heading">Contact</h2>`
and a `<ul>` of four `a.contact-link`, in this order. Source: the `contactLinks` array in
`app/content.ts`, rendered by `app/page.tsx`.

## Selectors

| # | `a.contact-link` href | Text | Opens |
|---|---|---|---|
| 1 | `mailto:ayoub003lkebch@gmail.com` | `ayoub003lkebch@gmail.com` | same tab (no `target`) |
| 2 | `https://www.linkedin.com/in/ayoublkebch` | `LinkedIn` | new tab |
| 3 | `https://github.com/itsAndL` | `GitHub` | new tab |
| 4 | `https://ayoublkebch.com` | `ayoublkebch.com` | new tab |

At ≤520px the links form an even 2×2 grid. The email and website links hold
`<span class="label-long">…</span><span class="label-short">Email|Website</span>` (only one shows
per breakpoint; the email's long label starts with an `aria-hidden` ✉) and an `aria-label` with the
full value, e.g. `Email ayoub003lkebch@gmail.com` / `Website ayoublkebch.com (opens in a new tab)`.

New-tab links carry `target="_blank" rel="noopener noreferrer"` and a visually hidden
" (opens in a new tab)".

## Check

```sh
python3 .claude/skills/verify-app/scripts/check_content.py <evidence>/dom.html contact
```
