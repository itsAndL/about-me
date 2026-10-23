# about-me

One-page About Me site for Ayoub Lkebch — who Ayoub is, the B2B products shipped so far, and how to get in touch. Plain HTML + CSS with no framework and no build step, published to GitHub Pages at https://itsandl.github.io/about-me/ (a sub-path, so every asset reference stays relative). Built with Fredrin.

## Run locally

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Run it from the repo root, then open http://127.0.0.1:8765/.

To launch, check and screenshot the page the way every ticket verifies it, follow `.claude/skills/verify-app/SKILL.md`.

## Deploy

Every push to `main` publishes the site to https://itsandl.github.io/about-me/ through the **Deploy to GitHub Pages** workflow (`.github/workflows/pages.yml`). It can also be run by hand from the Actions tab (`workflow_dispatch`).

The workflow copies the repo root into `_site/`, leaving out internal files (`.git`, `.github`, `.claude`, `.agents`, `.fredrin`, `README.md`), then uploads and deploys it with GitHub's official Pages actions. New files added at the root are published automatically. No secrets are needed.

**One-time setting:** in the repo's **Settings → Pages → Build and deployment**, set **Source** to **GitHub Actions**. Without it the deploy step fails. If you fork this repo, flip it in your fork too; the site then lives at `https://<your-user>.github.io/<repo>/`.
