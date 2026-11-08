# Contributing

This repository is a public reference platform and portfolio piece. Keep application source under `app/`, preserve the root command and Compose service contracts, and update requirement traceability when implementing a product requirement.

Before opening a change, run the relevant focused tests and `python scripts/check.py` when its dependent tooling is available. Do not commit secrets; copy `.env.example` to `.env` for local configuration.

Use focused commits. Changes that affect architecture should include an ADR under `docs/adr/`.
