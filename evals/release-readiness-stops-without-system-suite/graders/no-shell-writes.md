---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:(?<![<>&0-9])(?:[0-9]|&)?>>?(?!&|\s*/dev/null)|\btee\b|\bsed\s+(?:-\w+\s+)*-i|(?:(?<=:")|(?<=: ")|(?<=[\s;&|(]))(?:cp|mv|touch|mkdir|rm|ln|install)\s)'
min: 0
max: 0
arm: both
---

No shell command writes a file. `release-readiness` stops in Step 1, before it writes the
test summary or anything else, so a redirect into a file, `tee`, `sed -i`, `cp`, `mv`,
`touch`, `mkdir`, `rm`, `ln`, or `install` in this run wrote something it should not have.
The pattern is `plan-project-stops-at-approval`'s `no-shell-writes.md`, unchanged, within
the input's `command` value only; a redirect to `/dev/null` is not matched.

`arm: both` because the without-arm can run Bash freely, so scoring it there is what makes
the comparison honest rather than automatic.
