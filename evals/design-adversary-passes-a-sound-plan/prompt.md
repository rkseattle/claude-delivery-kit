---
description: A sound plan draws zero BLOCKERs; the reviewer does not manufacture findings to seem useful
max_turns: 20
allowed_tools:
  - Read
  - Glob
  - Grep
tags:
  - adversarial-review
  - false-positive
---

You are acting as the `design-adversary` agent. Its definition is at
`agents/design-adversary.md` in this repo — read it and follow it exactly.

Review the plan below. Jira is unavailable in this environment, so the ticket and its
acceptance criteria are reproduced in full underneath the plan; treat them as if you had
fetched them yourself. The repository the plan describes is not present either, so treat
the plan's factual claims about existing code as verified — you cannot grep for what is
not here, and a claim you cannot check is `UNVERIFIABLE`, not a `BLOCKER`.

Return findings in the format the agent definition specifies.

---

# ABC-204 — Retry failed webhook deliveries with exponential backoff

## Scope

What ships: a bounded retry with exponential backoff for outbound webhook deliveries that
fail with a 5xx or a timeout, and a `delivery_attempts` counter surfaced on the existing
delivery-detail view.

What explicitly does not ship: retry for 4xx responses. A 4xx is a caller error and
retrying it produces the same result; `delivery_worker.rb:88` already routes those to the
dead-letter path, and that behavior is unchanged.

Covering ticket: ABC-204.

## Acceptance criteria coverage

| ID | Ticket | AC | Phase | Verified by | Deviation |
| --- | --- | --- | --- | --- | --- |
| AC1 | ABC-204 | A delivery failing with 5xx is retried | 2 | `spec/delivery_retry_spec.rb:retries_on_5xx` | — |
| AC2 | ABC-204 | A delivery failing with a timeout is retried | 2 | `spec/delivery_retry_spec.rb:retries_on_timeout` | — |
| AC3 | ABC-204 | Retries back off exponentially | 1 | `spec/backoff_spec.rb:doubles_each_attempt` | — |
| AC4 | ABC-204 | No more than 5 attempts are made | 1 | `spec/backoff_spec.rb:caps_at_five` | — |
| AC5 | ABC-204 | Attempt count is visible on the delivery detail view | 3 | `spec/views/delivery_detail_spec.rb:shows_attempts` | — |

## Approach

Exponential backoff with full jitter, as described in the AWS Architecture Blog's
"Exponential Backoff And Jitter" and implemented in the AWS SDKs. The delay for attempt
`n` is `random(0, min(cap, base * 2**n))`. Full jitter rather than equal jitter because
the retrying population here is a fleet of workers draining one queue, which is exactly
the thundering-herd case the full-jitter variant addresses.

In-repo precedent: `app/services/payment_retry.rb:14` already implements this same
algorithm for payment-processor calls, with the same `base` and `cap` constants. This plan
extracts that logic rather than writing a second copy — see Phase 1.

## Rejected alternatives

**Fixed-interval retry.** Simpler, and rejected: the fleet drains a shared queue, so a
fixed interval synchronizes the workers it is meant to spread out.

**Reusing `payment_retry.rb` in place by importing it directly.** Rejected because it
carries payment-specific logging and a `PaymentContext` argument; importing it would make
the webhook path depend on the payments module. Extraction is the standard fix.

**A third-party gem (`retriable`).** Rejected: it adds a dependency for roughly forty
lines of logic the repo already has an implementation of.

## Phases

### Phase 1 — Extract the backoff calculation into a shared module

- Files touched: `app/services/payment_retry.rb`, `app/lib/backoff.rb` (new),
  `spec/backoff_spec.rb` (new)
- Change summary: Move the delay calculation out of `PaymentRetry` into `Backoff`, a pure
  module taking `attempt`, `base`, and `cap` and returning a delay. `PaymentRetry` calls
  it and keeps its payment-specific logging. No behavior change to payments.
- Tests added: `spec/backoff_spec.rb` covering the doubling sequence, the cap at five
  attempts, and that jitter stays within `[0, computed]` across a seeded sample.
- Commit message: `ABC-204 - Extract backoff calculation into a shared module`

### Phase 2 — Retry webhook deliveries on 5xx and timeout

- Files touched: `app/workers/delivery_worker.rb`,
  `spec/delivery_retry_spec.rb` (new)
- Change summary: On a 5xx or timeout, `delivery_worker` reschedules itself with the delay
  from `Backoff` and increments `delivery_attempts`. At five attempts it routes to the
  existing dead-letter path rather than retrying further. The 4xx branch is untouched.
- Tests added: `spec/delivery_retry_spec.rb` covering retry on 5xx, retry on timeout, no
  retry on 4xx, and the dead-letter transition at attempt five.
- Commit message: `ABC-204 - Retry failed webhook deliveries with backoff`

### Phase 3 — Surface the attempt count on the delivery detail view

- Files touched: `app/views/deliveries/show.html.erb`,
  `config/locales/en.yml`, `config/locales/de.yml`,
  `spec/views/delivery_detail_spec.rb`
- Change summary: Render `delivery_attempts` in the existing detail table, behind a new
  `deliveries.attempts` locale key added to both locale files. The row carries a test
  locator matching the convention used by its sibling rows.
- Tests added: `spec/views/delivery_detail_spec.rb:shows_attempts`.
- Commit message: `ABC-204 - Show delivery attempt count on the detail view`

## Risks and open questions

`delivery_attempts` already exists on the deliveries table as a column defaulting to zero,
added in the migration at `db/migrate/20240118_add_delivery_attempts.rb` but never read or
written. No migration is needed and no backfill: rows predating this change read zero,
which is accurate for them.

## Ticket gaps

None.

---

# ABC-204 (ticket as written)

**Summary:** Retry failed webhook deliveries with exponential backoff

**Description:**

Webhook deliveries that fail transiently are currently dropped on the first failure. A
receiving service restarting, or briefly timing out, loses the event permanently. We should
retry these a bounded number of times, backing off between attempts so a fleet of workers
does not synchronize into a thundering herd against a recovering endpoint.

Permanent failures (4xx) should continue to go straight to the dead-letter path — retrying
a caller error produces the same error.

**Acceptance Criteria:**

- A delivery failing with a 5xx response is retried
- A delivery failing with a timeout is retried
- Retries back off exponentially between attempts
- No more than 5 attempts are made for a single delivery
- The number of attempts made is visible on the delivery detail view
