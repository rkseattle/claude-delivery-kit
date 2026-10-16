---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<![\w\\"-]))git(?:\s|\\t)(?:(?:[^|;&()\\"]|\\[^nt])*?(?:\s|\\t))?(?:(?:switch|commit|push|add|stash|tag)\b|branch(?:\s|\\t)+(?:[^-\s\\"]|-[cCmM]\b)|checkout\s+(?:-[bB]|[^-\s\\"])|update-ref\s+(?:\\")?refs/heads/)'
min: 0
max: 0
arm: both
---

No branch is cut and nothing is committed before the sponsor answers. `plan-project`
stages and commits the brief on `brief/<slug>` only after recording the sponsor's
decision. The pattern matches `git` followed, within one shell command, by `add`, `switch`,
`commit`, `push`, `stash`, `tag`, `checkout -b` or `checkout <branch>`, `branch <name>`,
`branch -m` or `-c`, or `update-ref refs/heads/…`, whatever global options sit between
them, within the input's `command` value only; a separator, a newline, a subshell paren,
or the value's closing quote ends the command. Read-only commands —
`status`, `rev-parse`, `fetch`, `branch --show-current` — are not matched. A `grep` for one
of those words would be, which costs a false failure rather than a missed one.

`arm: both` because the without-arm can run Bash freely, so scoring it there is what makes
the comparison honest rather than automatic.
