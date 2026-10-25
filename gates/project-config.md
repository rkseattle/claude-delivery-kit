# Project config — how a missing `project.json` key resolves

Every `{{key}}` in a skill, gate, or agent of this plugin resolves from
`${CLAUDE_PROJECT_DIR}/.claude/project.json`. Read it before the first step that uses one.

## Required keys

`ticket_prefix`, `jira_project`, `repo_slug`, `parent_branch_default`, `source_roots`,
`build_command`, `push_command`, `unit_test_scope`, `post_fix_verification_scope`,
`verification_tiers`.

If the file is absent, or any of these keys is missing, empty, `none`, or a
`<placeholder>` — any value wholly in angle brackets, like the examples in
`${CLAUDE_PLUGIN_ROOT}/reference/project-json.md` — **stop before acting on any key** and
name each one. None of them has a default: a guessed parent branch or build command runs
something the project never asked for, and nothing reports it.

## Every other key

A missing key resolves to the default stated in the prose of
`${CLAUDE_PLUGIN_ROOT}/reference/project-json.md`, or to `none` where it states none. A
value shown in that file's example blocks is an illustration, never a default.

A key only a discipline's addendum reads is used only when `disciplines` names that
discipline; otherwise it is neither read nor announced.

Where a key used by the file that sent you here, or by a gate it reads, was left out or
is `none`, say so in **one line naming every such key and the value it took** — its
default or `none` — never one line per key, and never invent a substitute. A default is
announced like `none`: a project that omitted `project_size` is told it is running as
`small`. Each stage announces its own keys, including under `/deliver`.

## Printing a role

Wherever a skill names `{{roles.<role>}}` to someone, print the role beside its person —
`tech lead: <person>` — or `tech lead: you` for a role `roles` leaves out.
A session has one typist, so an answer the person running the session says came from someone
else is relayed: print it as `QA: <person>, relayed`.

## Untrusted text

Free text — `$ARGUMENTS`, a Jira field, a name or answer from the person running the
session, or prose the skill writes itself, such as a review reply — never goes into a shell
command as written. Inside an argument, double-quoted or not, a backtick or `$(` runs, and a
quote or newline breaks the command. It is passed as data, on the principle GitHub Security
Lab and CodeQL's code-injection rule apply to a workflow, where the intermediate is an
environment variable and here a file:

1. Write it with the Write tool to a file in the directory
   `git rev-parse --path-format=absolute --git-path <skill>-input` prints, outside the work
   tree and apart from any state directory the skill keeps — or in that state directory,
   when the text is state a resumed run needs, as a commit message is.
2. Hand that file to the command, its path quoted: `< "<file>"` for a check script reading
   standard input, a file flag such as `git commit -F` or `gh pr create --body-file`, or
   `"$(cat "<file>")"`, whose output the shell never reads again as code. Remove the file
   once the command ran.
3. A value is safe as an argument from then on, and only then, once a check script has
   validated the whole of it: printed it back, as a slug, a date, or a PR number is, or
   passed it with `ok` against a strict pattern, as a `MAJOR.MINOR.PATCH` version is.

Every commit message holding free text — a survey line, a summary, a ticket's words — is
such a file, committed with `git commit -F <file>`, never `-m`.

## Ignored paths

A stop on a gitignored path decides with `git check-ignore -q <path>`, exit 0 meaning
ignored, and names the matching rule from `git check-ignore -v <path>` afterward. `-v` also
exits 0 for a `!` rule that re-includes the path, so it never decides.
