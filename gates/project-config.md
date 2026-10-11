# Project config — how a missing `project.json` key resolves

Every `{{key}}` in a skill, gate, or agent of this plugin resolves from
`${CLAUDE_PROJECT_DIR}/.claude/project.json`. Read it before the first step that uses one.

## Required keys

`ticket_prefix`, `jira_project`, `repo_slug`, `parent_branch_default`, `source_roots`,
`build_command`, `push_command`, `unit_test_scope`, `post_fix_verification_scope`,
`verification_tiers`.

If the file is absent, or any of these keys is missing from it, **stop before acting on
any key** and name each missing one. None of them has a default: a guessed parent branch
or build command runs something the project never asked for, and nothing reports it.

## Every other key

A missing key resolves to the default given in `${CLAUDE_PLUGIN_ROOT}/README.md`'s
`project.json` section, or to `none` where that section gives none.

Where a key used by the file that sent you here is `none` — set that way or left out —
say so in **one line naming every such key**, never one line per key, and never invent a
substitute. Each stage announces its own `none` keys, including under `/deliver`.
