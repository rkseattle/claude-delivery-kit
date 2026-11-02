---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:(?<![<>&0-9])(?:[0-9]|&)?>>?(?![>&]|\s*/dev/null)|\btee\b|\bsed\s+(?:-\w+\s+)*-i|(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<=[\s;&|(]))(?:cp|mv|touch|ln|install)\s)|"command"\s*:\s*"(?:[^"\\]|\\.)*?(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<=[\s;&|(]))(?:mkdir|rm)\s(?!(?:[^;&|"\\]|\\[^nt])*?review-tickets)(?!(?:-\S+\s+)*(?:--\s+)?(?:\\"\$\{?\w+\}?(?:/[^\s"\\]*)?\\"|\$\{?\w+\}?(?:/[^\s"\;&|]*)?)(?:\s+(?:\\"\$\{?\w+\}?(?:/[^\s"\\]*)?\\"|\$\{?\w+\}?(?:/[^\s"\;&|]*)?))*\s*(?:[;&|)]|\\[nt]|"(?![\w$])))|"command"\s*:\s*"(?!(?:[^"\\]|\\.)*?review-tickets)(?:[^"\\]|\\.)*?(?:(?<=:")|(?<=: ")|(?<=\\n)|(?<=\\t)|(?<=[\s;&|(]))(?:mkdir|rm)\s(?=(?:-\S+\s+)*(?:--\s+)?(?:\\"\$\{?\w+\}?(?:/[^\s"\\]*)?\\"|\$\{?\w+\}?(?:/[^\s"\;&|]*)?)(?:\s+(?:\\"\$\{?\w+\}?(?:/[^\s"\\]*)?\\"|\$\{?\w+\}?(?:/[^\s"\;&|]*)?))*\s*(?:[;&|)]|\\[nt]|"(?![\w$])))'
min: 0
max: 0
arm: both
---

No shell command writes a file, other than an `rm` or `mkdir` of
`.git/review-tickets/`, `.git/review-tickets-input/`, or a file in either; `rmdir`, which
removes only an empty directory, is not matched. `review-tickets`
writes its input files and draft with the Write tool and changes nothing in the work tree,
so a redirect into a file, `tee`, `sed -i`, `cp`, `mv`, `touch`, `mkdir`, `rm`, `ln`, or
`install` elsewhere wrote where it must not. The pattern is
`plan-project-stops-at-approval`'s `no-shell-writes`, its exemption naming this skill's
directories; its notes on what it matches and misses hold here.
