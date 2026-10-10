# AGENTS.md — tar1090-tracker-carto

Home Assistant add-on repository: one add-on (`tar1090/`) that draws a
[tar1090](https://github.com/wiedehopf/tar1090) ADS-B feed on a Leaflet map
inside Home Assistant. Fork of `random-robbie/tar1090-tracker` (see README).
Python/Flask + vanilla JS — no compiled code, no test suite, no push CI.

## Structure

```
repository.json                     # HA add-on repository descriptor (no version field)
tar1090/config.yaml                 # add-on manifest — the version lives here and nowhere else
tar1090/build.yaml                  # HA base image 3.22 per arch + OCI labels
tar1090/Dockerfile                  # python3 + flask/requests/waitress, CMD /usr/bin/run.sh
tar1090/rootfs/usr/bin/run.sh       # reads /data/options.json, exports env, starts the app
tar1090/rootfs/app/app.py           # Flask app + all /api/* endpoints
tar1090/rootfs/var/www/tar1090/     # index.html, script.js, style.css, vendored Leaflet + MapLibre
CHANGELOG.md                        # repo-level changelog (trimmed copy of the add-on one)
tar1090/CHANGELOG.md                # add-on changelog — full history
scripts/release.sh                  # the release tool — use it, never hand-bump
.github/workflows/release.yml       # tag-triggered only: publishes the GitHub Release
simple-start.sh                     # standalone run outside HA
```

## Release process

One command, from a clean `main`:

```bash
./scripts/release.sh 1.3.1 "Faster start-up and a lighter dashboard poll"
```

It bumps `tar1090/config.yaml`, promotes `## [Unreleased]` → `## [<version>] - <date>`
in **both** changelogs (the summary becomes the section's first line), commits
`🔖 Release version <version>`, tags `v<version>`, and pushes `main` plus the tag.
It refuses to run unless you are on `main`, the tree is clean, the tag is new,
and both changelogs have an `## [Unreleased]` heading.

Order matters — **write the changelog entries first and commit them**, then run
the script. `release.yml` extracts everything under `## [<version>]` from
`CHANGELOG.md` and fails the Release job when that is whitespace-only, so an
empty `## [Unreleased]` plus no summary gives you a successful tag with a failed
workflow and no Release page. Style: `### Added / Changed / Fixed / Removed /
Technical`, one bold-lead bullet per change, wrapped near 76 columns.

Versioning follows the existing history: **minor** for features (1.2.1 → 1.3.0,
Trails), **patch** for fixes and internal changes. Commit messages carry no
attribution trailers.

## An already-shipped number doesn't count again

Supervisor compares the version *string* in `tar1090/config.yaml` and nothing
else — tree contents, commit dates and file hashes are invisible to it. Same
number on both sides ⇒ no delta ⇒ no Update button, no matter how many commits
landed. So any commit that reaches `main` after the last bump is **unreachable**
until a new number ships: store and install both read the old one, and reloading
the store or re-adding the repository cannot surface it.

That is exactly what happened here. `2d4ec64` released **1.3.0**, then
`eef99f1` (OCI labels, release-script trailers) and `925c31f` (single-pass
option reads, halved dashboard polling) landed on top **without a bump**, so
`config.yaml` still read 1.3.0 and HA offered nothing — those two commits were
undeliverable until `e27b9af` bumped to **1.3.1**.

Sanity check before pushing — the `config.yaml` line must be the *newer* of the
two; if the add-on files name a commit that came after it, the version is stale:

```bash
git log --oneline -1 -- tar1090/config.yaml   # last bump
git log --oneline -1 -- tar1090/rootfs        # last add-on change
```

There is no push CI in this repo, so nothing catches a missed bump for you.

## Gotchas

- **A push is the whole deploy.** `config.yaml` has no `image:` key, so
  Supervisor builds the image on the HA host from the git repo — there is no
  registry to publish to. But HA caches the add-on listing and the repository
  clone under `/data/addons/git/<hash>`; after a bump, **⋮ → Check for updates**
  plus a browser hard-refresh is what makes a new version appear.
- **Never read options through the Supervisor API.** `run.sh` reads
  `/data/options.json` — the 1.2.1 fix for the "Unable to access the API,
  forbidden" restart loop. Don't reintroduce `bashio::config`/API reads at
  start-up.
- **Edit both changelogs.** `CHANGELOG.md` is a trimmed copy of
  `tar1090/CHANGELOG.md` (same recent sections, older entries dropped); the
  release script rewrites both, so a hand release must too.
- **The Release workflow has never fired.** As of 2026-10-09 `gh api
  .../actions/runs` reports `total_count: 0` for the repo's entire history, and
  every release (v1.2.0, v1.2.1, v1.3.0, v1.3.1) is authored by `rainyvalley`
  rather than `github-actions[bot]`. The workflow is registered and `active`,
  but a tag push produces no run. If that is still true after a release, create
  the Release by hand with the notes the workflow would have used:
  `awk -v v=<version> 'index($0,"## ["v"]")==1{f=1;next} /^## \[/{f=0} f' CHANGELOG.md > notes.md`
  then `gh release create v<version> --title "Release <version>" --notes-file notes.md`.
