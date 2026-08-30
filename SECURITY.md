# Security Policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Contact the repository maintainer privately with a description, reproduction steps, affected version or commit, and potential impact.

This portfolio project uses seeded data and simulated integrations. It must not receive real payment details, production credentials, or personal customer data.

## Security baseline

Secrets belong only in local environment configuration and are excluded by `.gitignore`. Future work must validate input, enforce role-based access, redact sensitive data from logs, and use simulated payment references rather than card data.
