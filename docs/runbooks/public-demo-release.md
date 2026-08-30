# Public demo release

This runbook prepares the local portfolio scaffold for a future public release. It does not publish the repository, create a remote repository, or claim that a public release already exists.

## Intended public location

The intended public repository is [FishRaposo/entrega-clara](https://github.com/FishRaposo/entrega-clara). Before publishing, independently verify that this exact repository exists, is public, and uses `main` as its default branch. Do not invent a remote commit SHA or push to a similarly named repository.

## Local release gate

From the repository root, run the following commands and record their exit status:

```bash
make check
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
- After the intended remote is independently verified, add it, push `main` and `v0.1.0`, then inspect remote refs and the public README.

## Conditional publication sequence

Do not add a remote or push anything until the local release gate passes and this exact repository is independently verified as public with `main` as its default branch:

```bash
gh repo view FishRaposo/entrega-clara \
  --json nameWithOwner,url,visibility,defaultBranchRef
```

Stop if the command fails or its output does not identify `FishRaposo/entrega-clara`, `https://github.com/FishRaposo/entrega-clara`, `PUBLIC`, and default branch `main`. Only after that verification, run:

```bash
git remote -v
git remote add origin https://github.com/FishRaposo/entrega-clara.git
git remote get-url origin
git push -u origin main
git push origin v0.1.0
```

If `origin` already exists, do not overwrite it: verify `git remote get-url origin` is the exact canonical URL above before pushing. After both pushes succeed, verify the remote refs and inspect the README served from the public default branch:

```bash
git ls-remote --heads origin main
git ls-remote --tags origin v0.1.0
curl --fail --location --silent --show-error \
  https://raw.githubusercontent.com/FishRaposo/entrega-clara/main/README.md
```

Confirm the returned ref hashes match the intended local commit and tag, and inspect the public README for the verified setup commands and repository boundaries. A failed or mismatched check means publication is not verified and must not be reported as complete.

## Demo limitations

Present the project as a local, deterministic portfolio demonstration. Payments, GPS movement, map data, notifications, role switching, and operational identities are simulated or seeded. It does not process real funds or credentials, provide real authentication or courier verification, send provider notifications, or claim production certification, LGPD certification, or measured uptime.

## International example

The second market configuration is a coherent Canadian Toronto example (`ca`, `en-CA`, CAD, `America/Toronto`) and does not inherit PIX or Brazilian address/privacy copy.
