# The Gazette

Version 2.0.1

A weekly broadsheet by M.B. Parks, published from a GitHub repository
and deployed automatically to Cloudflare Pages.

Live at: **gazette.mbparks.com**

## The workflow

Publishing a new edition is three commands:

```bash
cp back-issue-template.html backissues/broadsheet-2026-07-10.html
# ... edit the file, fill in the four gazette-* meta tags ...
git add . && git commit -m "Vol. I, No. X" && git push
```

About sixty seconds later the new issue is live and appears in the
archive. There is no manifest to hand-edit, no cache to bust, no
deployment step. The four `gazette-*` meta tags in the HTML file are
the source of truth for both the file's existence and its metadata.

## Architecture

```
┌─────────────────────┐
│  Local editor       │  drop broadsheet-YYYY-MM-DD.html
│  git commit / push  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  GitHub repo        │  mbparks/gazette
│  main branch        │
└──────────┬──────────┘
           │  push triggers Action
           ▼
┌─────────────────────┐
│  GitHub Action      │  scripts/build-manifest.py
│  build-manifest.yml │  reads gazette-* meta tags
│                     │  writes manifest.json
│                     │  commits back to repo
└──────────┬──────────┘
           │  new commit
           ▼
┌─────────────────────┐
│  Cloudflare Pages   │  auto-deploys from main
│  gazette.mbparks.com│  serves static files
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Reader's browser   │  index.html fetches
│                     │  /manifest.json
│                     │  renders the archive
└─────────────────────┘
```

Two independent Cloudflare Pages deploys usually happen per push: one
for your commit that added the HTML file (deploys HTML but manifest is
stale), and one for the bot's follow-up commit that regenerated the
manifest (deploys the up-to-date manifest). For a minute or two the new
issue's HTML page exists but is not yet listed in the archive. This is
harmless: the direct URL works, the archive catches up.

## File layout

```
mbparks/gazette/
├── .github/workflows/
│   └── build-manifest.yml     GitHub Action
├── backissues/
│   ├── README.md
│   └── broadsheet-YYYY-MM-DD.html  (one per edition)
├── scripts/
│   └── build-manifest.py      Manifest generator
├── back-issue-template.html   Starting point for each edition
├── index.html                 Correspondence desk + archive
├── manifest.json              Auto-generated, do not hand-edit
├── requirements.txt           Python deps for the Action
├── wrangler.toml              Cloudflare deployment config
├── _headers                   Cloudflare Pages cache headers
├── .gitignore
└── README.md                  This file
```

## Meta tag convention

Every back-issue HTML file needs these four tags in its `<head>`:

```html
<meta name="gazette-volume"   content="I">
<meta name="gazette-number"   content="IX">
<meta name="gazette-headline" content="Fire the Lasers, Cumberland Bakes at 102 Degrees">
<meta name="gazette-subhead"  content="A field report from the shop floor in high summer">
```

If any tag is missing, the build script falls back:

- `gazette-headline`: uses `<title>` with "The Gazette :: " prefix and
  ":: M.B. Parks" suffix stripped
- `gazette-subhead`: uses `<meta name="description">`
- `gazette-volume`, `gazette-number`: empty (dateline just shows the date)

See `back-issue-template.html` for a minimal starting point.

## First-time setup

### 1. Create the repo

```bash
gh repo create mbparks/gazette --public --source=. --push
```

Or upload these files through the GitHub web UI. The bootstrap
`manifest.json` (empty) is included so the site renders on first load.

### 2. Connect Cloudflare Pages

Cloudflare has transitioned Pages projects to the "Workers with static
assets" pattern, so the build system runs `npx wrangler deploy` and
reads `wrangler.toml` at the repo root to know where the static files
live. That config file is included in this repo.

Steps:

- Cloudflare dashboard → Workers & Pages → Create → Pages → Connect to Git
- Pick the `mbparks/gazette` repo
- Framework preset: **None**
- Build command: leave blank
- Build output directory: leave blank (wrangler.toml handles it)
- Deploy

If your Cloudflare project name is not `gazette`, open `wrangler.toml`
and change the `name` field to match, then commit and push.

### 3. Add the custom domain

- Pages project → Custom domains → Set up a custom domain
- Enter `gazette.mbparks.com`
- Cloudflare handles DNS automatically since mbparks.com is already
  on Cloudflare

### 4. Publish the first issue

```bash
cp back-issue-template.html backissues/broadsheet-2026-07-10.html
# edit meta tags in the new file
git add backissues/broadsheet-2026-07-10.html
git commit -m "First edition"
git push
```

Watch the Action tab on GitHub, then the Deployments tab on Cloudflare.

## Testing locally

```bash
pip install -r requirements.txt
python scripts/build-manifest.py
python -m http.server 8000
# Open http://localhost:8000
```

The Python script is idempotent, running it locally does not commit
anything, it just rewrites `manifest.json`.

## Retiring the old Worker

The `gazettebackissues.mike-268.workers.dev` Worker from the previous
architecture is no longer needed. Once `gazette.mbparks.com` is live
and working, remove the Worker from the Cloudflare dashboard to keep
the deployment inventory clean.

## Known limitations

- **Two deploys per push.** Cloudflare Pages fires once for your
  commit and once for the bot's follow-up commit that regenerates
  the manifest. Wastes a small amount of build minutes but is
  otherwise harmless.
- **Manifest lag on first deploy.** For roughly a minute after
  pushing a new issue, the direct URL for the issue works but the
  archive listing still shows the previous state. Resolves when the
  second deploy completes.
- **No draft mode.** Every commit to `main` publishes. Use a feature
  branch for drafts and merge when ready.
- **No RSS/Atom feed.** Could be added by extending the build script
  to also emit `feed.xml`. Not included in 2.0.0.
- **Fonts loaded from Google Fonts.** Not fully local-first. Could
  be self-hosted in a later revision.
- **Filename is authoritative for date.** Renaming an issue file
  changes its "publication date" in the archive. Do not rename after
  publishing without meaning to.

## Changelog

**2.0.1**
- Added `wrangler.toml` at the repo root. Cloudflare's current CI runs
  `npx wrangler deploy` (Workers pattern) rather than the older
  `wrangler pages deploy`, and errors without a config file telling it
  where the static assets are. The `[assets] directory = "./"` block
  is the fix.

**2.0.0**
- Architectural shift. Files-as-source-of-truth, git-driven,
  Cloudflare Pages hosting.
- Cloudflare Worker retired.
- Manifest is now auto-generated by GitHub Action from meta tags
  in the HTML files themselves. No hand-editing.
- URL structure moved to `gazette.mbparks.com/` (subdomain root)
  instead of `mbparks.com/gazette.html`.
- Back issues at `/backissues/broadsheet-YYYY-MM-DD.html`.

**1.2.0**
- Filename convention set to `broadsheet-YYYY-MM-DD.html`.

**1.1.0**
- Worker filters out manifest entries whose HTML file does not exist.

**1.0.0**
- Initial release. Cloudflare Worker + hand-maintained manifest on
  x10hosting.

## License

GPL-3.0

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
