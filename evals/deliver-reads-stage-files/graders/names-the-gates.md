---
type: llm
---

The delivery workflow has five stages and two unconditional gates.

PASS when the answer names the Definition of Done as the gate before every commit and
the pre-push checklist as the gate before every push, and describes stages recognisably:
planning with an approval gate, phased implementation, a cold branch review, the PR, and
CI to green.

FAIL when the answer invents stages or gates that the workflow does not have, omits the
approval gate after planning, or describes the gates as optional or advisory.
