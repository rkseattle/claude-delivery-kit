---
type: llm
---

The workspace's `.claude/project.json` leaves out every optional key `review-tickets`
names, `design_dir`, `adr_dir`, and `brief_file` among them.

PASS when the response names `design_dir`, `adr_dir`, and `brief_file` together, in one
line or sentence, as left out or `none`, and the review still runs to its report.

FAIL when the response stops on any of them, invents a path for any, or never names them.
