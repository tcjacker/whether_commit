# Security Policy

## Supported Versions

This project is pre-1.0. Security fixes are applied to the default branch.

## Reporting a Vulnerability

Please report security issues privately before opening a public issue. Send a concise report to the project maintainers with:

- affected version or commit;
- steps to reproduce;
- expected impact;
- any relevant logs or sample input with secrets removed.

If this repository does not yet publish a dedicated security contact, open a minimal public issue asking for a private disclosure channel without including exploit details.

## Security Model

`backend-visiable` is designed for local development against trusted repositories. It can inspect git metadata, read source files, and aggregate local test or assessment evidence. Do not run it against untrusted repositories without reviewing the code and command paths first.

## Secrets

Never commit API keys, provider tokens, local `.env` files, or generated snapshot data. If a secret is committed, revoke or rotate it immediately and remove it from git history before publishing the repository.
