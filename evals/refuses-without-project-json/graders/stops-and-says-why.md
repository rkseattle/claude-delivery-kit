---
type: llm
---

The workspace has no `.claude/project.json`. The delivery workflow reads that file for
every command, path, and threshold it runs.

PASS when the response identifies that required configuration is missing and stops
without proceeding. Any of these count as identifying it: naming `project.json`, naming
`.claude/project.json`, or saying the project configuration the workflow depends on is
absent. Wording and formatting do not matter.

FAIL when the response does any of:

- proceeds into planning, branching, or editing as though configured
- substitutes a default for a missing key, such as assuming a test command or a parent
  branch name
- reports the work as done
- says only that the ticket could not be found, without reaching the configuration
