---
name: readme-docs
description: Write, rewrite, or audit a project's README.md and the companion docs it links to (CONTRIBUTING.md, SECURITY.md, docs/). Use whenever the user asks to create, improve, update, review, or "fix" a README or project documentation, asks for a quickstart or install instructions for a repo, or says the docs are out of date, even if they don't say "README".
---

# README and project docs

Produce a README that a stranger can use to understand the project, install it, and run a working example, with every command and link verified against the repo. Longer material goes in separate files that the README links to.

## Rules

1. Do not invent facts. Every install command, version, flag, env var, port, and URL must come from the repo (manifests, scripts, CI config, source) or from running it. If a fact can't be confirmed, leave a `<!-- TODO: confirm X -->` comment and list it in the final report.
2. Run what you document. Execute install, build, test, and quickstart commands in the session where feasible, in an isolated environment (a virtualenv, a container); never install system-wide or pipe a remote script to a shell without asking. Paste real output, trimmed, into examples. If a command can't be run (needs credentials, hardware, paid service), say so in the report.
3. Write plainly. No marketing adjectives ("blazing", "powerful", "seamless"), no emoji headers, no filler intros. State what the project does and support it.
4. Match length to audience (see Project types). Do not pad a small tool to fill a template.
5. Preserve what's correct in an existing README. Rewrite only sections that are wrong, missing, or unclear, and keep the author's terminology.

## Workflow

### 1. Discover

Read before writing. Collect facts into a scratch list with the file each came from.

- Manifests: `package.json`, `pyproject.toml`, `setup.cfg`, `Cargo.toml`, `go.mod`, `*.csproj`, `Package.swift`, `Gemfile`, `pom.xml`, `build.gradle`
- Build/run entry points: `Makefile`, `justfile`, `scripts/`, `Dockerfile`, `docker-compose.yml`, `Procfile`
- CI: `.github/workflows/`, `.gitlab-ci.yml`, `azure-pipelines.yml` (these show the real supported versions and test commands)
- Config surface: `.env.example`, config schemas, CLI arg parsers, `--help` output
- Existing docs: `README*`, `docs/`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `LICENSE`
- Repo metadata: `git remote -v`, default branch, tags/releases

### 2. Classify

Pick one project type. It decides which sections are required.

| Type | Reader's first question | Required beyond the core |
|---|---|---|
| Library / package | How do I call it? | API overview or link, supported versions |
| CLI tool | What command do I type? | Per-OS install, `--help` summary, common invocations |
| Service / app | How do I run it locally? | Prerequisites, config/env vars, run + test commands, architecture sketch |
| Framework / platform (large) | Where do I go? | Short README that routes to docs site, community, contributing |
| Internal / team repo | How do I get productive? | Owners, environments, deploy process, runbook links |

Core sections for every type: title + one-line description, install, minimal usage example, license. See `references/readme-template.md` for the full skeleton and per-type notes.

### 3. Update an existing README

Skip this step when there is no README yet. Otherwise map before writing, so nothing is regenerated away:

1. List every section of the current README, in order, with its heading anchor.
2. Map each one to a template section, to Standard Readme's extra-sections slot (after Usage and the template's Configuration, before API or Development) for content the template has no place for, such as Benchmarks or FAQ, or to a move into `docs/<topic>.md` or `CONTRIBUTING.md` per the Draft step's rules.
3. Verify every command, version, flag, and link in the old content against the repo, as rule 1 requires for new content: stale claims in old sections are the usual defect.
4. Anchors come from heading text, so reordering keeps them, except that GitHub numbers duplicate headings in order (`#example`, `#example-1`) and reordering those swaps them; renaming a heading (`Installing` → `Install`) or moving a section into another file breaks them. Before either, grep the repo for `README.md#<anchor>` and the README itself for `(#<anchor>)`. Where something links to it, keep the heading text, or make the change and list each broken link in the report. Links from outside the repo (a docs site, issues) cannot be grepped; the report says so.
5. Record each section as kept, edited, moved, added, or removed, with a one-line reason, for the report.

### 4. Draft

Copy the skeleton from `references/readme-template.md`, or, when updating, apply the map from step 3 to the existing file. Delete sections that don't apply instead of leaving them empty. Ordering follows Standard Readme (title, badges, description, TOC, security, background, install, usage, extra sections, API, maintainers, contributing, license), with deviations allowed when the project type calls for them.

Move content out of the README when:
- a section exceeds ~100 lines (API reference, full config reference, tutorials) → `docs/<topic>.md`
- it's contributor-only (dev setup, release process, code style) → `CONTRIBUTING.md`
- it's vulnerability reporting → `SECURITY.md`
- it's version history → `CHANGELOG.md`

Use relative links for in-repo files so they resolve on any branch.

### 5. Verify

Run `python3 <skill-dir>/scripts/check_readme.py README.md`, where `<skill-dir>` is the base directory shown when this skill loads. It checks size against GitHub's 500 KiB truncation limit, one H1 and no skipped heading levels, presence of install/usage/license sections, relative links (Markdown and HTML) that resolve, including `#section` anchors against GitHub's heading slugs, code fences without language tags, images without alt text, absolute local paths, length over 400 lines, and leftover template placeholders. A code span broken across lines can shift later line numbers in its paragraph by one. Fix every error. Review warnings.

Then check by hand:
- Run each fenced shell block in the quickstart, in order, from a clean checkout if possible.
- Confirm versions in the README match manifests and CI matrices.
- Confirm external URLs point to the intended pages (spot-check; don't fetch dozens).

### 6. Report

End the session with:
- Files created or changed
- When updating, every original section as kept, edited, moved, added, or removed, with its reason, and any anchors moved that other files link to
- Commands run to verify, and their results
- Facts left as TODO and why
- Sections intentionally omitted and why

## Quality bar

Score the result against `references/checklist.md` before reporting. Every "Must" item passes or is listed in the report with a reason.
