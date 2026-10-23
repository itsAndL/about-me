# Feature: SEO and social metadata

Source: `metadata` and `viewport` exports in `app/layout.tsx`; the icon and share-image file
conventions in `app/` (`icon.svg`, `icon.ico`, `apple-icon.png`, `opengraph-image.png`,
`twitter-image.png`, plus the `*.alt.txt` files); the JSON-LD `Person` in `app/page.tsx`;
static `public/robots.txt` and `public/sitemap.xml`.

`metadataBase` is `https://itsandl.github.io`; Next applies the `/about-me` base path to the
file-convention URLs itself. The 32px `.ico` is `app/icon.ico`, not `app/favicon.ico`: Next 16
only links `favicon.ico` when its URL is exactly `/favicon.ico`, so under a base path that file
ships but gets no `<link>`. Setting `metadata.icons` instead would switch off every icon file
convention.

## Tags in `out/index.html`

| Tag | Expected |
|---|---|
| `meta[name=description]` | `Ayoub Lkebch — full-stack product engineer in Casablanca, Morocco. …` |
| `link[rel=canonical]`, `meta[property="og:url"]` | `https://itsandl.github.io/about-me/` |
| `meta[property="og:image"]`, `meta[name="twitter:image"]` | `https://itsandl.github.io/about-me/{opengraph,twitter}-image.png?<hash>`, 1200×630, with alt |
| `meta[name="twitter:card"]` | `summary_large_image` |
| `meta[name=theme-color]` × 2 | `#fbfaf7` (light), `#111312` (dark) |
| `link[rel=icon]` × 2, `link[rel=apple-touch-icon]` | `/about-me/icon.svg?…`, `/about-me/icon.ico?…`, `/about-me/apple-icon.png?…` |
| `script[type="application/ld+json"]` | one `Person`, `url` `https://itsandl.github.io/about-me/` |

`out/404.html` (`app/not-found.tsx`) overrides the root metadata: `noindex`, no canonical.

## Check

```sh
npm run build && python3 .claude/skills/verify-app/scripts/doctor.py .   # lines starting "metadata:"
```

`run.sh all` runs it with `--served`, which also fetches the share images, `robots.txt` and
`sitemap.xml` over HTTP under `/about-me/`. Social previews themselves (LinkedIn Post Inspector,
opengraph.xyz) can only be checked against the live URL after a deploy.
