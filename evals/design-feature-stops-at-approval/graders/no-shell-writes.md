---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:(?<![<>&0-9])(?:[0-9]|&)?>>?(?!&|\s*/dev/null)|\btee\b|\bsed\s+(?:-\w+\s+)*-i|(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<=[\s;&|(]))(?:cp|mv|touch|ln|install)\s)|"command"\s*:\s*"(?!(?:[^"\\]|\\.)*design-feature-input)(?:[^"\\]|\\.)*?(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<=[\s;&|(]))(?:mkdir|rm)\s'
min: 0
max: 0
arm: both
---

No shell command writes a file, other than removing an input file under
`.git/design-feature-input/`, or making that directory, in a Bash call that names it.
`design-feature` writes nothing else before the tech lead answers, and writes the design
doc and its ADRs with the Write or Edit tool, so a redirect into a file, `tee`, `sed -i`,
`cp`, `mv`, `touch`, `mkdir`, `rm`, `ln`, or `install` in this run wrote outside them. The
scaffold makes `docs/design` and `docs/adr`, so a compliant run needs no `mkdir` there.

The exemption covers `rm` and `mkdir` alone: every other verb, and every redirect, is
checked in a call that names the input directory too, so `echo x > src/a && rm <input
file>` fails. A `rm` or `mkdir` chained into such a call is not caught. A command after an
escaped newline or tab is checked. A literal `\n` in a command's text, or a heredoc line
starting with one of those verbs, is matched too, a false failure rather than a missed
write. A write from inside an interpreter, such as `python3 -c`, is not caught here. Only
the input's `command` value is read, never its description. Redirects to `/dev/null` and
to another descriptor, as in `2>&1`, and input redirects such as `< "<file>"` are not
matched; `2>file` and `&>file` are.
