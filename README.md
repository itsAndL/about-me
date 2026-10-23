# about-me

One-page About Me site for Ayoub Lkebch — who Ayoub is, the B2B products shipped so far, and how to get in touch. Built with Next.js 16 + TypeScript (App Router) as a fully static export, published to GitHub Pages at https://itsandl.github.io/about-me/. No server, database or runtime env vars. Built with Fredrin.

The page copy lives in `app/content.ts` (projects, contact links) and `app/page.tsx` (intro, footer). Static files such as favicons, the share image, `robots.txt` and `sitemap.xml` live in `public/`.

## Run locally

Needs Node.js 20.9 or newer.

```sh
npm ci
npm run dev
```

Then open http://localhost:3000/about-me/ — the site lives under the `/about-me` base path, in dev too.

## Build

```sh
npm run build
```

This writes the static site to `out/` (`next.config.ts` sets `output: "export"`, `basePath: "/about-me"` and `trailingSlash: true`). To serve the export the way Pages does, launch, check and screenshot it, follow `.claude/skills/verify-app/SKILL.md`, or run `.claude/skills/verify-app/scripts/run.sh all`.

Checks: `npx tsc --noEmit` and `npm run lint`.

## Deploy

Every push to `main` publishes the site to https://itsandl.github.io/about-me/ through the **Deploy to GitHub Pages** workflow (`.github/workflows/pages.yml`). It can also be run by hand from the Actions tab (`workflow_dispatch`).

The workflow installs dependencies with `npm ci`, runs `npm run build`, then uploads `out/` and deploys it with GitHub's official Pages actions. Only the built export is published, never the repo source. No secrets are needed.

Every asset URL must carry the `/about-me` base path: use `next/link`, the metadata file conventions or base-path-aware imports, never a hard-coded root-absolute `/…` path.

**One-time setting:** in the repo's **Settings → Pages → Build and deployment**, set **Source** to **GitHub Actions**. Without it the deploy step fails. If you fork this repo, flip it in your fork too, and change `basePath` in `next.config.ts` to your repo name; the site then lives at `https://<your-user>.github.io/<repo>/`.
