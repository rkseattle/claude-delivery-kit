# Project config — how a missing `project.json` key resolves

Every `{{key}}` in a skill, gate, or agent of this plugin resolves from
`${CLAUDE_PROJECT_DIR}/.claude/project.json`. Read it before the first step that uses one.

## Required keys

`ticket_prefix`, `jira_project`, `repo_slug`, `parent_branch_default`, `source_roots`,
`build_command`, `push_command`, `unit_test_scope`, `post_fix_verification_scope`,
`verification_tiers`.

If the file is absent, or any of these keys is missing, empty, `none`, or still a README
placeholder in angle brackets, **stop before acting on any key** and name each one. None of them has a default: a guessed parent branch
or build command runs something the project never asked for, and nothing reports it.

## Every other key

A missing key resolves to the default stated in the prose of
`${CLAUDE_PLUGIN_ROOT}/README.md`'s `project.json` section, or to `none` where it states
none. A value shown in that section's example blocks is an illustration, never a default.

Where a key used by the file that sent you here, or by a gate it reads, was left out or
is `none`, say so in **one line naming every such key and the value it took** — its
default or `none` — never one line per key, and never invent a substitute. A default is
announced like `none`: a project that omitted `project_size` is told it is running as
`small`. Each stage announces its own keys, including under `/deliver`.

## Printing a role

Wherever a skill names `{{roles.<role>}}` to someone, print the role beside its person —
`tech lead: <person>` — or `tech lead: you` for a role `roles` leaves out.
