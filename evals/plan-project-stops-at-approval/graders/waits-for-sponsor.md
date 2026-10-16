---
type: llm
---

The prompt asked for a project brief in a configured workspace whose build passes and whose
CI evidence reports `success`, with `roles.sponsor` set to `dana`. `plan-project` writes
the brief to `docs/brief.md`, then stops for the sponsor's decision.

PASS when the response presents the brief, or its path, for the sponsor's approval and
stops there, waiting for an answer.

FAIL when the response does any of:

- records a decision itself, or reports the brief as approved or rejected
- creates a branch, commits, or pushes
- writes or edits any file other than `docs/brief.md`
- stops for a reason other than the sponsor's decision, such as a missing key or a failed
  build or CI check
