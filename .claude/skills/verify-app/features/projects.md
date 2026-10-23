# Feature: projects ("Shipped")

`section.projects[aria-labelledby="shipped-heading"]` with `<h2 id="shipped-heading">Shipped</h2>`
and a `<ul>` of exactly four `li.project`, in this order. Source: the `projects` array in
`app/content.ts`, rendered by `app/page.tsx`.

## Selectors

Each `li.project` holds `h3.project-name`, `a.project-link` (bare domain + `↗` in an
`aria-hidden` span + a visually hidden " (opens in a new tab)") and `p.project-desc`.
Only Opilote has `span.badge` (`Building now`) inside its `.project-name`.

| # | `.project-name` | `.project-link` href / text | `.project-desc` |
|---|---|---|---|
| 1 | Opilote + `.badge` "Building now" | `https://opilote.com` / `opilote.com` | GPS fleet-management SaaS I'm building end to end: Rails API, React web app, React Native app live on Google Play. |
| 2 | Timlead | `https://getstarted.timlead.com` / `getstarted.timlead.com` | Field-service platform used by 6,000+ people. I built its AI assistant and MCP server. |
| 3 | TestSkills | `https://testskills.app` / `testskills.app` | Skills-assessment and hiring platform I led from the first commit. |
| 4 | Humaneo | `https://humaneo.ma` / `humaneo.ma` | HR SaaS used by 7,000+ employees. |

Every `.project-link` has `target="_blank" rel="noopener noreferrer"`.

## Check

```sh
python3 .claude/skills/verify-app/scripts/check_content.py <evidence>/dom.html projects
curl -s http://127.0.0.1:8765/about-me/ | grep -o 'class="project"' | wc -l   # 4 (export is one line)
```
