#!/usr/bin/env bash
# A project.json, the agent's rules file, and one design doc that meets every design-exit
# rule. Its partner case's scaffold writes the same doc with rollout step 3's rollback
# removed, so the two differ by that one line.
set -euo pipefail
mkdir -p .claude docs/design
cat > .claude/project.json <<'JSON'
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "parent_branch_default": "main",
  "source_roots": "api worker db",
  "build_command": "make build",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "unit_test_scope": "the whole target",
  "post_fix_verification_scope": "everything",
  "verification_tiers": "ci · inspection",
  "design_dir": "docs/design",
  "adr_dir": "docs/adr",
  "disciplines": [],
  "roles": { "tech_lead": "abc-lead" }
}
JSON
mkdir -p .claude/agent-rules
cat > .claude/agent-rules/feature-design-adversary.md <<'RULES'
# feature-design-adversary rules

- The repository this design describes is not in this workspace: there is no git history
  and none of the files `Current state` cites. A claim about that code cannot be checked,
  so it is UNVERIFIABLE, never a BLOCKER.
RULES
cat > docs/design/per-endpoint-webhook-rate-limits.md <<'MD'
# Per-endpoint webhook rate limits

## Summary

A customer can cap how many webhook deliveries per second ABC sends to each of their
endpoints. Today the delivery worker sends every delivery as soon as it is dequeued, so a
burst of events reaches a receiver at once. The cap is an optional setting on the endpoint,
stored in the existing `endpoint_settings` table and enforced in the worker by a
sliding-window log in Redis, so a delivery over the cap waits in the queue instead of being
sent.

## Motivation

A receiver that cannot absorb a burst answers with HTTP 429, and each rejected delivery is
retried up to eight times, adding load while the receiver is weakest. The only workaround
today is pausing the endpoint, which delays every event sent to it.

## Goals

- A customer sets a deliveries-per-second cap on an endpoint, and the worker never exceeds it.
- An endpoint with no cap is delivered to exactly as today.

## Non-goals

- Caps shared across several endpoints, or set per account.
- Changing the retry schedule for failed deliveries.

## Success measures

- SM1: Deliveries sent above an endpoint's cap in any one-second window: 0 by general availability
- SM2: Share of deliveries to capped endpoints answered with HTTP 429: < 1% by 30 days after general availability

## Current state

- `worker/dispatcher.py:42` sends each delivery as soon as it is dequeued, with no pacing.
- `worker/dispatcher.py:77` re-enqueues a failed delivery with exponential backoff, up to
  eight attempts.
- `worker/settings_reader.py:15` loads an endpoint's `endpoint_settings` rows and its flag
  values once per delivery batch.
- `api/settings/validator.py:7` holds `ALLOWED_SETTING_KEYS`, the keys the settings API
  accepts.
- `db/migrations/0031_endpoint_settings.sql:1` creates `endpoint_settings (endpoint_id,
  key, value)`, keyed on `(endpoint_id, key)`.

## Survey

- **Svix** — an endpoint's `throttleRate` caps messages per second sent to it, holding the
  rest back; Svix documents the cap as approximate: https://docs.svix.com/throttling
- **Hookdeck** — a destination's max delivery rate, per second, minute, or hour, queues
  events that arrive faster and delivers them later:
  https://hookdeck.com/docs/guides/control-throughput-queue-events
- **Convoy** — each endpoint takes a rate limit and a rate-limit duration that together
  bound the events sent to it: https://www.getconvoy.io/docs/glossary/rate-limiting-endpoints

## Options

- **A sliding-window log per endpoint (chosen).** Wins: like all three surveyed systems it
  queues deliveries over the cap rather than dropping them, and unlike an approximate cap it
  never sends more than the cap in any one-second window, which SM1 requires.
- **A token bucket per endpoint.** Loses: a full bucket of one second's tokens plus a
  second's refill sends up to twice the cap in one second, which breaks SM1.
- **Backing off on the receiver's 429s.** Loses: the receiver is already overloaded by the
  time it answers, which is the problem being solved.
- **Do nothing.** Loses: customers keep pausing endpoints, and 429 retries keep adding load.

## Proposal

The settings API accepts `delivery.rate_limit_per_second`, a positive integer, and stores it
as an `endpoint_settings` row. Before each send to an endpoint with that row, the dispatcher
asks `rate_limiter` for a slot; with none free, it re-enqueues the delivery with a delay of
the time until the oldest send leaves the window. Enforcement is behind the
`endpoint_rate_limits` flag. No choice here is costly to reverse: the setting is a row in an
existing key-value table, the window is a Redis key that expires, and the flag turns
enforcement off.

## Components and interfaces

```mermaid
flowchart LR
  customer[Customer] --> api
  flags[Flag service] --> worker
  subgraph abc[ABC webhooks]
    api[Settings API] --> pg[(Postgres)]
    queue[(Delivery queue)] --> worker[Delivery worker]
    worker --> queue
    worker --> pg
    worker --> redis[(Redis)]
  end
  worker --> receiver[Customer webhook receiver]
```

```mermaid
flowchart LR
  settings_routes --> settings_validator
  settings_routes --> settings_repository
```

```mermaid
flowchart LR
  dispatcher --> settings_reader
  dispatcher --> rate_limiter
  dispatcher --> http_sender
```

### settings_routes

- Responsibility: serve the endpoint settings API.
- Inputs: `PUT /endpoints/{id}/settings/{key}` from a customer, with a JSON value.
- Outputs: 204 on a stored setting.
- Errors: 400 with the validator's message for a rejected key or value; 404 for an unknown endpoint.
- Versioning: new keys are additive; the route shape does not change.
- Layer: presentation

### settings_validator

- Responsibility: decide whether a setting key and value may be stored.
- Inputs: a key and a value from `settings_routes`.
- Outputs: the normalized value; `delivery.rate_limit_per_second` must be an integer of at least 1.
- Errors: a rejection naming the key and the rule it broke.
- Versioning: a key is added to `ALLOWED_SETTING_KEYS`, never renamed.
- Layer: domain logic

### settings_repository

- Responsibility: read and write `endpoint_settings` rows.
- Inputs: an endpoint ID, key, and value from `settings_routes`.
- Outputs: the stored row.
- Errors: a database error, surfaced to the route as 503.
- Versioning: unchanged; the table is key-value.
- Layer: data access

### dispatcher

- Responsibility: send each dequeued delivery, pacing capped endpoints.
- Inputs: deliveries from the queue; settings and flags from `settings_reader`; a slot or a wait from `rate_limiter`.
- Outputs: a send through `http_sender`, or a re-enqueue with a delay.
- Errors: a failed send is re-enqueued with backoff, as today.
- Versioning: internal; no caller outside the worker.
- Layer: domain logic

### settings_reader

- Responsibility: load an endpoint's settings rows and flag values.
- Inputs: an endpoint ID from `dispatcher`.
- Outputs: the endpoint's settings and its `endpoint_rate_limits` flag value.
- Errors: a database or flag-service error fails the batch, which is retried, as today.
- Versioning: unchanged.
- Layer: data access

### rate_limiter

- Responsibility: atomically record a send for an endpoint in Redis if it fits under the cap.
- Inputs: an endpoint ID, a delivery ID, and the cap from `dispatcher`.
- Outputs: `slot`, or `wait <ms>` until the oldest send leaves the one-second window.
- Errors: a Redis error or a 50 ms timeout returns `wait 1000`, so an outage delays capped endpoints rather than exceeding their caps.
- Versioning: new; its one call is internal to the worker.
- Layer: data access

### http_sender

- Responsibility: POST a delivery to its endpoint's URL.
- Inputs: a delivery from `dispatcher`.
- Outputs: the receiver's status code.
- Errors: a timeout or non-2xx status, returned to `dispatcher`.
- Versioning: unchanged.
- Layer: integration

## Likely changes

- The limiting algorithm, should bursts above the cap ever be allowed — hidden behind `rate_limiter`.

## Data model and ownership

- `endpoint_settings`: a row with key `delivery.rate_limit_per_second` and an integer value
  of at least 1, for an endpoint in `endpoints` by `endpoint_id`. No schema change.
- Redis `ratelimit:<endpoint_id>`: a sorted set whose members are delivery IDs, scored by
  send time in milliseconds, holding the last second's sends; it expires 2 seconds after the
  last send.

| Store | Owning module |
| --- | --- |
| Postgres `endpoint_settings` | `settings_repository` |
| Redis `ratelimit:<endpoint_id>` | `rate_limiter` |

## Non-functional requirements

- NFR1: ≤ 5 ms added to p99 dispatch latency for a capped endpoint — rate_limiter: one Redis script call per delivery, with a 50 ms timeout

## Rollout and rollback

1. Deploy the settings API that accepts the key. Rollback: redeploy the previous API release.
2. Deploy the worker with `endpoint_rate_limits` off. Rollback: redeploy the previous worker.
3. Turn on `endpoint_rate_limits` for the five internal test endpoints. Rollback: turn it off for them.
4. Turn on `endpoint_rate_limits` for every endpoint. Rollback: turn it off for every endpoint.

## Observability

- A `rate_limit_wait` log line per re-enqueue, with the endpoint ID and the delay.
- Metrics `webhook_rate_limited_total` and `rate_limiter_errors_total`, by endpoint.
- An alert when `rate_limiter_errors_total` rises for 5 minutes.

## Test strategy

| Level | Risks covered |
| --- | --- |
| unit | The window admits more than the cap in a second, or a value under 1 is stored as a cap |
| integration | Two workers against one Redis send above the cap, because the script is not atomic |
| system | Uncapped endpoints are delayed: a staging run compares their p99 latency with the flag on and off |
| acceptance | A cap set through the API holds through a 10-second burst to a test receiver, counted per second |

Coverage target: 100% line coverage of `rate_limiter` and of the dispatcher's wait path.

## Drawbacks

- Each delivery to a capped endpoint costs a Redis round trip.
- A capped endpoint's events arrive later during a burst, by design.

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| Redis outage delays every capped endpoint | low | capped deliveries wait until Redis returns | the `rate_limiter_errors_total` alert | abc-lead |
| A low cap backs up a busy endpoint's queue | medium | that endpoint's events arrive minutes late | the API docs state the delay; the wait metric shows it | product owner |
| Clock skew between workers widens the window | low | a second's sends exceed the cap slightly | the script reads Redis `TIME`, not the worker clock | abc-lead |
| The extra Redis call exceeds NFR1 | low | slower dispatch for capped endpoints | the system-level latency comparison before step 4 | abc-lead |
| Customers set no cap, so SM2 does not move | medium | the 429 rate stays as today | support suggests a cap on each 429 ticket | product owner |

## Work plan

### Handoff: webhook-rate-limits

Delivers: SM1, SM2
Estimated changed lines: 320

- Accept a per-endpoint rate limit in the settings API
  - Phase 1 — Allow and validate `delivery.rate_limit_per_second`
- Pace deliveries to rate-limited endpoints
  - Phase 1 — Add the sliding-window rate limiter
  - Phase 2 — Wait in the dispatcher behind the flag

## Open questions

none — every choice is settled in the sections above.

## Decision

Pending — abc-lead.
MD
