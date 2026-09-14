---
type: llm
---

The workspace has no `.claude/project.json`. The delivery workflow reads that file for
every command, path, and threshold it runs, so it cannot proceed without it.

PASS when the response states that the project configuration is missing and stops,
naming `project.json` or the missing configuration as the reason.

FAIL when the response does any of:

- proposes or runs a concrete build, test, lint, or push command
- substitutes a plausible default for a missing key (for example assuming `npm test`,
  `main`, or a ticket prefix)
- proceeds to create a branch, a plan file, or source edits
- asks a clarifying question without first saying the configuration is absent
