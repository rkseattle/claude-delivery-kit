---
type: llm
---

The plan's `Threat model` rates three STRIDE categories `High` for
`Webhooks::StripeController`. **Spoofing** and **Tampering** each name Phase 1, which
delivers the signature check that mitigates them. **Denial of service** names no phase: its
`Mitigating phase` cell is `—`, and its own note says the public endpoint runs an HMAC over
every request body before it can reject one. Nothing in the plan rate-limits the endpoint,
caps the body size, or otherwise mitigates it.

`design-adversary.md` makes a `Threat model` row rated `High` that names no phase a
BLOCKER — its fifth kind.

PASS when the response reports the `High` denial-of-service threat as a BLOCKER because no
phase mitigates it.

FAIL when the response does any of:

- does not mention the denial-of-service row at all
- mentions it only as MAJOR, MINOR, or UNVERIFIABLE
- describes it as a possible omission or asks whether it was intentional, rather than
  reporting it as a defect
- reports the Spoofing or Tampering row as a BLOCKER for lacking a mitigating phase, since
  each names Phase 1
- reports a `Low` row with `—` as a BLOCKER, since only `High` must name a phase
- reports the `Medium` Repudiation row as a BLOCKER for its phase cell, since it names Phase 2

Other findings, at any severity, do not affect the grade.
