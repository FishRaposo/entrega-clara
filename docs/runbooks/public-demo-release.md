# Public demo release

This runbook records the release gate for the public demo at [FishRaposo/entrega-clara](https://github.com/FishRaposo/entrega-clara). The repository is public and uses `main`; a release tag is created only after the local gate passes. The checklist does not publish anything by itself.

## Public location

Verify the public remote before pushing a release: the exact repository exists, is public, uses `main` as its default branch, and its `origin` URL is the canonical one. Do not invent a remote commit SHA or push to a similarly named repository.

## Local release gate

From the repository root, run the following commands and record their exit status:

```bash
python scripts/check.py
python scripts/data/validate_seed.py data/scenarios/lunch-rush.json
python scripts/quality/check_requirement_coverage.py docs/requirements/traceability.md
python scripts/repo/check_app_boundary.py
python -m pytest tests -q
cd app/web && npm test -- --run && npm run typecheck && npm run build
git status --short
git diff --check
git ls-files -z | python -c 'import sys; from scripts.repo.print_tree import _safe_parts; paths = sys.stdin.buffer.read().decode().split("\0"); print("\n".join(path for path in paths if path and _safe_parts(path) is None))'
```

The final command audits tracked paths only, using the renderer's exact safety rules; it does not inspect untracked files. It reports `.env` files, secret/credential/key/certificate-like names and suffixes, and generated or dependency paths including caches, build/dist output, coverage, `node_modules`, `__pycache__`, `.egg-info`, and `.tsbuildinfo`. Review every reported path: the tracked `.env.example` is the only intentional exception; any other report is a release blocker. Private `.superpowers/` task state must not be tracked, while `docs/superpowers/specs/` is public documentation and must remain visible.

`docker compose config` is a separate local check. If Docker is unavailable, record it as **unverified locally**; do not report it as passed. Do not start the stack or represent its health endpoints as verified when the Compose check cannot run.

## Public-demo checklist

- Confirm the tree renderer emits only filtered Git-tracked paths: `python scripts/repo/print_tree.py`.
- Confirm tracked files contain no secrets, credentials, keys, certificates, generated artifacts, dependencies, or `.superpowers/` paths with the command above, allowing only `.env.example`. This is a tracked-file audit only; untracked files are outside its scope.
- Confirm the governing seed design, application source, `docs/`, `tests/`, and `scripts/` are present.
- Confirm README setup commands match the commands that passed locally.
- Create the local release commit and annotated `v0.1.0` tag only after all runnable local checks pass.
- Push `main` and `v0.1.0` only after the gate passes and the remote check agrees; then inspect the remote refs and the public README.

## Verify the public remote

Run the local gate first, then verify the public remote before pushing a release tag:

```bash
gh repo view FishRaposo/entrega-clara \
  --json nameWithOwner,url,visibility,defaultBranchRef
git remote get-url origin
git ls-remote --heads origin main
git ls-remote --tags origin v0.1.0
```

Stop if the repository is not public, the default branch is not `main`, or `origin` is not `https://github.com/FishRaposo/entrega-clara.git`. Push `main` and `v0.1.0` only after the gate passes and those checks agree. After pushing, compare the remote ref hashes with the local commit and tag, and inspect the README served from the public default branch:

```bash
curl --fail --location --silent --show-error \
  https://raw.githubusercontent.com/FishRaposo/entrega-clara/main/README.md
```

A failed or mismatched check means the release is not verified and must not be reported as complete.

## Demo limitations

Present the project as a local, deterministic portfolio demonstration. Payments, GPS movement, map data, notifications, role switching, and operational identities are simulated or seeded. It does not process real funds or credentials, provide real authentication or courier verification, send provider notifications, or claim production certification, LGPD certification, or measured uptime.

## International example

The second market configuration is a coherent Canadian Toronto example (`ca`, `en-CA`, CAD, `America/Toronto`) and does not inherit PIX or Brazilian address/privacy copy.
