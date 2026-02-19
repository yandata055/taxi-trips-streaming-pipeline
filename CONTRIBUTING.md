---
noteId: "980574900d5d11f1aab8b5fb1cd2812e"
tags: []

---

# Contributing

How to contribute and how we keep the evolution visible on GitHub.

## Workflow: branch, change, PR, then CHANGELOG

1. **Branch** from `main`: e.g. `feature/glue-replay-fix`, `docs/changelog-initial`, `fix/producer-typo`.
2. **Make changes** (code and/or docs). Update [docs/project_structure.md](docs/project_structure.md) if you add or rename directories.
3. **Open a PR** against `main`. Title: short description of what changed. Description: why and impact.
4. **Merge** (squash or keep one logical commit per change so history stays readable).
5. **Update CHANGELOG**: add an entry under `[Unreleased]` (and move it under a new version when you cut a release). Use categories: Added, Changed, Fixed, Deprecated, Removed, Security.

## Commit messages

Use a short prefix so `git log` and release notes are clear:

- `feat: ...` — new behaviour or feature
- `fix: ...` — bug fix
- `docs: ...` — documentation only
- `infra: ...` — IaC or deployment
- `refactor: ...` — code structure, no behaviour change
- `test: ...` — tests only

Example: `fix: Glue replay use sqs_url and DynamoDB Table resource`.

## Releases

See [docs/release-guide.md](docs/release-guide.md) for how to create a tag and GitHub Release and paste the relevant CHANGELOG section.

## ADR (Architecture Decision Records)

For non-trivial design decisions, add a short ADR under `docs/decisions/`, e.g. `001-use-kinesis-for-ingestion.md`. Include: context, decision, consequences. Reference the ADR in the PR that implements it.
