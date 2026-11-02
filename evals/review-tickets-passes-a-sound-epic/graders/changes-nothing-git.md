---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<![\w\\"-]))git(?:\s|\\t)(?:(?:[^|;&()\\"]|\\[^nt])*?(?:\s|\\t))?(?:(?:switch|commit|push|add|stash|tag|reset|merge|rebase|pull|cherry-pick|revert|rm|mv|restore|update-index|apply)\b|checkout\s+--(?:\s|\\t)|branch(?:\s|\\t)+(?:[^-\s\\"]|-[cCmMdDf]\b)|worktree(?:\s|\\t)+(?:add|remove)\b|checkout\s+(?:-[bB]|[^-\s\\"])|update-ref\s+(?:\\")?refs/heads/)'
min: 0
max: 0
arm: both
---

A review moves no branch and changes no index or tracked file: no `add`, `commit`, `push`,
`stash`, `tag`, `reset`, `merge`, `rebase`, `pull`, `cherry-pick`, `revert`, `rm`, `mv`,
`restore`, `update-index`, `apply`, `switch`, `checkout --` or `checkout <branch>`, `branch`
with a name or `-d`, `-D`, `-f`, or `worktree add` or `remove`; the skill's own worktree is
added and removed by `design_check.py`, not by a git command it runs. The
pattern is `design-feature-runs-from-a-feature-branch`'s `no-branch-or-commit` with those
verbs added.
