---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:(?<![<>&0-9])(?:[0-9]|&)?>>?(?!&|\s*/dev/null)|\btee\b|\bsed\s+(?:-\w+\s+)*-i|(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<=[\s;&|(]))(?:cp|mv|touch|mkdir|rm|ln|install)\s)'
min: 0
max: 0
arm: both
---

No shell command writes a file. `release-readiness` stops in Step 1, before it writes the
test summary or anything else, so a redirect into a file, `tee`, `sed -i`, `cp`, `mv`,
`touch`, `mkdir`, `rm`, `ln`, or `install` in this run wrote something it should not have.
The pattern is `plan-project-stops-at-approval`'s `no-shell-writes.md` less its
input-directory exemption, within the input's `command` value only; a command after an
escaped newline or tab is checked too, and a redirect to `/dev/null` is not matched. A
literal `\n` in a command's text, or a heredoc line starting with one of those verbs, is
matched too, a false failure rather than a missed write.

`arm: both` because the without-arm can run Bash freely, so scoring it there is what makes
the comparison honest rather than automatic.
