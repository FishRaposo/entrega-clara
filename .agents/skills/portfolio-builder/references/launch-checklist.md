# Launch checklist

## Pre-flight

- [ ] Fresh clone in a clean directory; the documented commands work without external infrastructure.
- [ ] Latest CI run on the default branch is green (not just a workflow file); the badge matches reality.
- [ ] Tests, lint, types and generated-artifact checks pass locally.
- [ ] No secrets, tokens, private keys or real customer data (`git log -p | grep -i` for known
      patterns; check media too).
- [ ] License present; third-party data attributed (e.g. ODbL for OpenStreetMap).
- [ ] Media regenerated and committed; the screenshots match the current UI.
- [ ] Links checked in the README and the reviewer page; every relative link resolves, every external
      link is intentional.

## Repo card

| Field | Checklist |
| --- | --- |
| Description | One sentence; what + who + proof; not a tagline |
| Topics | 6–10; domain, stack, technique, data; lowercase/hyphenated |
| Homepage | Live demo or docs URL |
| Social preview | 1280×640 image; name + one number |
| Pin | Pin the repo on the profile |
| Profile README | Links the repo with one line of context |

### Commands

```bash
# GitHub Pages, once per repository (POST; use PUT if Pages already exists)
gh api --method POST repos/<owner>/<repo>/pages -f build_type=workflow
gh workflow run pages.yml
gh run watch <run-id> --exit-status

# Repo card
gh repo edit --description "<what + who + proof>" --homepage <url>
gh repo edit --add-topic pathfinding --add-topic routing --add-topic ...
```

## Social preview

GitHub has no REST or GraphQL endpoint for the social preview: upload
`docs/media/social-preview.png` in Settings → Social preview. Commit the 1280×640 asset so it is
reproducible; the mechanical audit checks its dimensions.

## Hosting

- **Static replay or docs:** GitHub Pages from a committed `site/` (or `docs/`) directory via Actions.
  No server, no secrets.
- **API:** a container platform (Fly, Render, Railway) with the database optional; environment
  variables set in the platform, never committed.
- **Web app:** Vercel/Netlify with the API origin set as an environment variable; browser calls stay
  same-origin through a rewrite.
- **Deployment is an operator action:** the repository ships the artifacts and the runbook; CI does not
  deploy without explicit credentials.

## Media budgets

| Asset | Target | Hard limit |
| --- | --- | --- |
| GIF | ≤ 500 KB | 1 MB |
| Video | ≤ 3 MB | 5 MB |
| Screenshot | ≤ 150 KB | 300 KB |
| Social preview | 1280×640 | 1 MB |

Compress, crop and loop. Large media belongs behind a link, not in the repository.

## Post-launch verification

- [ ] Run `python .agents/skills/portfolio-builder/scripts/portfolio_audit.py . --remote --network --claims`.
- [ ] Open every link in the README and reviewer page from a private window; no 404s, no login walls.
- [ ] Upload the social preview in Settings and confirm the repo card renders it.
- [ ] Open the demo on a phone; the first screen is still readable.
- [ ] Ask someone who has never seen the project to take the 60-second test; note where they stop.
- [ ] Confirm CI is green *after* the launch changes.
- [ ] Record the launch date and the commit in the verification document.

## Consent checklist

Public changes need explicit approval from the owner:

- enabling Pages or any hosting;
- changing the repository description, topics, homepage or social preview;
- pinning the repository;
- making a private repository public;
- posting the link to external platforms.
