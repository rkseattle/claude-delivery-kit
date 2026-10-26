---
type: file_exists
path: '.claude/**'
exists: false
---

The run created no file matching `.claude/**`: the configuration directory; the skill
writes no state before Step 6. Read from the workspace after the run, this catches a write
the `tool_used` graders miss, such as one from inside an interpreter. A file the scaffold
made and the run only edited is invisible here, which `no-other-edit` covers. The globs
are prefix-scoped so they mean the same whether or not `*` crosses `/`, which the harness
does not document.
