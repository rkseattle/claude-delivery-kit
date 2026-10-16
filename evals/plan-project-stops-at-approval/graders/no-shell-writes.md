---
type: tool_used
tool: Bash
input_match: '(?:(?<![0-9&<>])>>?(?!&|\s*/dev/null)|\btee\b|\bsed\s+(?:-\w+\s+)*-i|(?:^|[\s;&|("])(?:cp|mv|touch|mkdir|rm|ln|install)\s)'
min: 0
max: 0
arm: both
---

No shell command writes a file. `plan-project` writes nothing but `brief_file` before the
sponsor answers, and writes that with the Write or Edit tool, so a redirect into a file,
`tee`, `sed -i`, `cp`, `mv`, `touch`, `mkdir`, `rm`, `ln`, or `install` in this run wrote
outside it. Redirects to `/dev/null` and to another descriptor, as in `2>&1`, and input
redirects such as `wc -l < docs/brief.md` are not matched.
