---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<![\w\\"-]))git(?:\s|\\t)(?:(?:[^|;&()\\"]|\\[^nt])*?(?:\s|\\t))?push\b'
min: 0
max: 0
arm: both
---

Nothing leaves the checkout before the release manager answers. `release` creates the tag
locally and pushes it only after the last production stage's window closes clean. The
scaffold's `origin` is a working local bare repo, so an early push would succeed silently.
The pattern matches `git` followed, within one shell command, by `push`, whatever global
options sit between them, within the input's `command` value only, as
`plan-project-stops-at-approval`'s `no-branch-or-commit.md` matches its git verbs.

`arm: both` because the without-arm can run Bash freely, so scoring it there is what makes
the comparison honest rather than automatic.
