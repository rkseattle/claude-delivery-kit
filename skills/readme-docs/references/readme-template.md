# README skeleton

Copy, fill, and delete what doesn't apply. HTML comments are instructions; remove them in the final file.

````markdown
# project-name
<!-- Must match the repo and package names. If they differ, explain in the description. -->

<!-- Badges (optional, max ~5): build status, latest version, license, coverage. Only badges backed by a real, working service. -->

One sentence: what it is and what problem it solves, for someone who has never heard of it.

<!-- Optional second paragraph: who it's for, how it differs from the obvious alternative, current status (alpha / stable / maintenance-only). -->

<!-- Optional: one screenshot, GIF, or terminal recording if the project is visual or interactive. Store it in the repo (e.g. docs/img/), not a hotlinked URL. -->

## Contents
<!-- Include only if the README has more than ~6 sections. GitHub auto-generates a TOC in its UI; other renderers don't. -->

## Security
<!-- Only if SECURITY.md exists or should. Standard Readme places it right after the table of contents. -->
Report vulnerabilities as described in [SECURITY.md](SECURITY.md).

## Install

<!-- Prerequisites with versions, sourced from manifests/CI. -->
Requires: RUNTIME-NAME VERSION-RANGE, OTHER-DEPS.

<!-- One block per supported method, most common first.
     CLI tools: per-OS commands (Homebrew, apt, winget/scoop, cargo/pip/npm, release binaries).
     Services: clone + dependency install + env setup. -->
```sh
INSTALL-COMMAND
```

## Usage

<!-- The smallest example that does something real. Show the command AND trimmed actual output. -->
```sh
EXAMPLE-COMMAND
```
```text
REAL-OUTPUT
```

<!-- Then 2–5 common tasks, each a short heading + example. Link to docs/ for the rest. -->

## Configuration
<!-- Services and CLIs with options. Source from .env.example / arg parser. Move to docs/configuration.md if > ~20 entries. -->

| Variable | Default | Description |
|---|---|---|
| `EXAMPLE_VAR` | `value` | What it controls |

## Development
<!-- Short: how to run tests and build locally. Full contributor setup goes in CONTRIBUTING.md. -->
```sh
TEST-COMMAND-FROM-CI
```

## Documentation
<!-- Links to docs/, docs site, API reference, FAQ, changelog. -->

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md).

## License
SPDX-ID — see [LICENSE](LICENSE).
````

Placeholders are written in CAPS-WITH-HYPHENS so `scripts/check_readme.py` can flag any left behind.

## Per-type notes

**Library / package**
- Usage shows import, one call, and the result.
- State supported language/runtime versions and where the API reference lives.
- Model: tiangolo/fastapi (runnable example that grows step by step).

**CLI tool**
- Include a trimmed `--help` or a table of the most-used commands.
- Per-OS install is expected. Release binaries need the download URL pattern.
- A "why use this / why not" section helps when there are well-known alternatives.
- Model: BurntSushi/ripgrep (benchmarks, per-OS install, GUIDE.md and FAQ.md split out).

**Service / app**
- Prerequisites (DB, queue, cloud credentials) up front.
- One path from clone to running locally, ideally a single `docker compose up` or `make dev`.
- A short architecture section: components and how they talk. A Mermaid diagram is fine.

**Framework / platform (large)**
- Keep the README short. It's a directory: what this is, where docs live, how to get help, how to contribute.
- Model: kubernetes/kubernetes.

**Internal / team repo**
- Owning team and contact channel.
- Environments (dev/staging/prod), how to deploy, where dashboards and runbooks are.
- On-call or escalation link if applicable.
