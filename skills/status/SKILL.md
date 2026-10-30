---
name: status
description: Report where a feature stands between design and tickets — its lifecycle state and the one command that moves it on — without starting a run. Changes nothing but its input file and a fetch.
argument-hint: <design path> | <EPIC-KEY>
disable-model-invocation: true
allowed-tools: Read, Write, Bash, mcp__atlassian__jira_search
---

Report the lifecycle state of: $ARGUMENTS

Read `${CLAUDE_PROJECT_DIR}/.claude/project.json`: `{{ticket_prefix}}` and
`{{parent_branch_default}}` come from it. Read `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md`
and follow it exactly. This skill changes nothing: it writes only its input file, and
it never edits, commits, switches a branch, or transitions a ticket.

1. With `$ARGUMENTS` empty, ask for a design path or an Epic key, and stop.
2. Write `$ARGUMENTS` to a file per **Untrusted text** in `gates/project-config.md`. It is
   an Epic key when this prints it back:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" ticket-key --prefix "{{ticket_prefix}}" < "<arguments file>"
   ```

3. Run `git fetch origin {{parent_branch_default}}`. If it fails, say the state is read
   from the last fetch.
4. Run this, adding `--epic` for an Epic key:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" lifecycle --ref "origin/{{parent_branch_default}}" --config "<absolute project root>/.claude/project.json" < "<arguments file>"
   ```

5. Print its two lines as they are. On `INVALID:`, print that line and stop.
6. For an Epic key, add one line from `jira_search` with `parent = <KEY>`: each child's key
   and status, or `no children`. When the search fails, the line says child statuses are
   unavailable and quotes the error. The script is offline, so Jira is this step's alone.
   Never let Jira change the state or the `NEXT:` line.
