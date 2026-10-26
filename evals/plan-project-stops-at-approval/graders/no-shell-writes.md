---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:(?<![<>&0-9])(?:[0-9]|&)?>>?(?![>&]|\s*/dev/null)|\btee\b|\bsed\s+(?:-\w+\s+)*-i|(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<=[\s;&|(]))(?:cp|mv|touch|ln|install)\s)|"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<=[\s;&|(]))(?:mkdir|rm)\s(?!(?:[^;&|"\\]|\\[^nt])*?plan-project-input)(?!(?:-\S+\s+)*(?:--\s+)?(?:\\"\$\{?\w+\}?(?:/[^\s"\\]*)?\\"|\$\{?\w+\}?(?:/[^\s"\;&|]*)?)(?:\s+(?:\\"\$\{?\w+\}?(?:/[^\s"\\]*)?\\"|\$\{?\w+\}?(?:/[^\s"\;&|]*)?))*\s*(?:[;&|)]|\\[nt]|"(?![\w$])))|"command"\s*:\s*"(?!(?:[^"\\]|\\.)*?plan-project-input)(?:[^"\\]|\\.)*?(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<=[\s;&|(]))(?:mkdir|rm)\s(?=(?:-\S+\s+)*(?:--\s+)?(?:\\"\$\{?\w+\}?(?:/[^\s"\\]*)?\\"|\$\{?\w+\}?(?:/[^\s"\;&|]*)?)(?:\s+(?:\\"\$\{?\w+\}?(?:/[^\s"\\]*)?\\"|\$\{?\w+\}?(?:/[^\s"\;&|]*)?))*\s*(?:[;&|)]|\\[nt]|"(?![\w$])))'
min: 0
max: 0
arm: both
---

No shell command writes a file, other than an `rm` or `mkdir` of the input directory
`.git/plan-project-input/` or a file in it. `plan-project` writes nothing else before the
sponsor answers, and writes the brief with the Write or Edit tool, so a redirect into a
file, `tee`, `sed -i`, `cp`, `mv`, `touch`, `mkdir`, `rm`, `ln`, or `install` in this run
wrote outside it.

The exemption is per command: an `rm` or `mkdir` is exempt when its own command, up to the
next `;`, `&`, `|`, or newline, names the input directory, or when its operands are only
shell variables, such as `rm -- "$f"`, in a Bash call that names the directory. So `rm -rf
src && rm <input file>` fails, while `rm -rf src <input file>`, one command naming both,
and a variable pointing elsewhere are not caught. Every other verb, and every redirect, is
always checked.

A command after an escaped newline or tab is checked. A literal `\n` in a command's text,
a heredoc line starting with one of those verbs, or a `>` inside a quoted string, as in
`git log --format="<%ae>"`, is matched too, a false failure rather than a missed write. A
write from inside an interpreter, such as `python3 -c`, is not caught here.

Only the input's `command` value is read, never its description. Redirects to `/dev/null`,
with `>` or `>>`, and to another descriptor, as in `2>&1`, and input redirects such as `<
"<file>"` are not matched; `2>file` and `&>file` are.
