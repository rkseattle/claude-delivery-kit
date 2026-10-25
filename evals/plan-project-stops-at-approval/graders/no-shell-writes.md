---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?!(?:[^"\\]|\\.)*plan-project-input)(?:[^"\\]|\\.)*?(?:(?<![<>&0-9])(?:[0-9]|&)?>>?(?!&|\s*/dev/null)|\btee\b|\bsed\s+(?:-\w+\s+)*-i|(?:(?<=:")|(?<=: ")|(?<=[\s;&|(]))(?:cp|mv|touch|mkdir|rm|ln|install)\s)'
min: 0
max: 0
arm: both
---

No shell command writes a file, other than removing the project name's input file under
`.git/plan-project-input/`. `plan-project` writes nothing else before the sponsor answers,
and writes the brief with the Write or Edit tool, so a redirect into a file,
`tee`, `sed -i`, `cp`, `mv`, `touch`, `mkdir`, `rm`, `ln`, or `install` in this run wrote
outside it. A write from inside an interpreter, such as `python3 -c`, is not caught here. Only the input's `command` value is read, never its description. Redirects to `/dev/null`
and to another descriptor, as in `2>&1`, and input redirects such as
`wc -l < docs/brief.md` are not matched; `2>file` and `&>file` are.
