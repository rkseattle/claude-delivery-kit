---
type: tool_used
tool: Write
input_match: "\"file_path\"\\s*:\\s*\"[^\"]*docs/releases/1\\.0\\.0-notes\\.md\""
min: 1
---

The run wrote the release notes to `docs/releases/1.0.0-notes.md` before asking. `release`
tags, builds once, and writes its notes before the staging ask, so a reply that asks
without them has skipped the steps the release manager is being asked to build on.
