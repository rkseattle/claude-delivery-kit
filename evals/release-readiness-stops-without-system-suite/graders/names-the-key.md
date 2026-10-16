---
type: regex
target: last_message
match: contains
pattern: "system_test_command"
---

The reply names the missing key. `.claude/project.json` sets every required key and
`release_dir`, and leaves out only `system_test_command`. This is a weak signal on its own:
the one-line announcement `gates/project-config.md` requires names the key whether or not
the run stops, so `no-summary-write`, `no-shell-writes`, and the llm grader are what show
the stop.
