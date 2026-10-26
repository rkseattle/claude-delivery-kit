---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?!(?:[^"\\]|\\.)*design-feature-input)(?:[^"\\]|\\.)*?(?:(?<![<>&0-9])(?:[0-9]|&)?>>?(?!&|\s*/dev/null)|\btee\b|\bsed\s+(?:-\w+\s+)*-i|(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=[\s;&|(]))(?:cp|mv|touch|mkdir|rm|ln|install)\s)'
min: 0
max: 0
arm: both
---

No shell command writes a file, other than in a call naming the input directory
`.git/design-feature-input/`, where the skill removes each input file once the command it
fed has run. `design-feature` writes nothing else before the tech lead answers, and writes
the design doc and its ADRs with the Write or Edit tool, so a redirect into a file, `tee`,
`sed -i`, `cp`, `mv`, `touch`, `mkdir`, `rm`, `ln`, or `install` in this run wrote outside
them. The scaffold makes `docs/design` and `docs/adr`, so a compliant run needs no `mkdir`.

The pattern is `plan-project-stops-at-approval`'s, its input directory renamed, with a
command after an escaped newline checked too. The exemption covers the whole Bash call, so
a write chained in the same call as an input file's cleanup, such as
`rm -rf src && rm <input file>`, is not caught; nor is a write from inside an interpreter,
such as `python3 -c`. Only the input's `command` value is read, never its description.
Redirects to `/dev/null` and to another descriptor, as in `2>&1`, and input redirects such
as `design_check.py slug < "<file>"` are not matched; `2>file` and `&>file` are.
