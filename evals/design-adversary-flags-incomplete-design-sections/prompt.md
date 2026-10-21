---
description: Incomplete design sections are MAJORs, not BLOCKERs, cited against the plan section rather than code
max_turns: 20
allowed_tools:
  - Read
  - Glob
  - Grep
tags:
  - adversarial-review
  - regression
---

You are acting as the `design-adversary` agent. Its definition is at
`agents/design-adversary.md` in this repo — read it and follow it exactly.

Review the plan below. Jira is unavailable in this environment, so the ticket and its
acceptance criteria are reproduced in full underneath the plan; treat them as if you had
fetched them yourself. The ticket's parent Epic, ABC-230, is reproduced after it. The
repository the plan describes is not present either, so treat the plan's factual claims
about existing code as verified — you cannot grep for what is not here, and a claim you
cannot check is `UNVERIFIABLE`, not a `BLOCKER`.

Return findings in the format the agent definition specifies.

---

# ABC-231 — Download delivery history as a zipped CSV

## Scope

What ships: a zipped CSV of a user's last 90 days of webhook deliveries, streamed from the
delivery history view.

What explicitly does not ship: JSON export. The ticket asks for CSV only.

Covering ticket: ABC-231.

## Acceptance criteria coverage

| ID | Ticket | AC | Phase | Verified by | Deviation |
| --- | --- | --- | --- | --- | --- |
| AC1 | ABC-231 | A user can download their delivery history as a zipped CSV | 2 | `spec/exports/delivery_export_spec.rb:zipped_csv` | — |
| AC2 | ABC-231 | The export includes every delivery from the last 90 days | 1 | `spec/queries/delivery_history_query_spec.rb:covers_90_days` | — |
| AC3 | ABC-231 | NFR1: an export of 100,000 deliveries completes in under 30 seconds | 2 | `spec/perf/delivery_export_perf_spec.rb:under_30s` | — |

## Approach

Surveyed: GitHub's repository archive download, Stripe's report runs, and Shopify's bulk
operations export all stream large exports as compressed files rather than building them in
memory, and all three paginate the underlying query by keyset. This plan follows GitHub's
shape — a synchronous streamed download — because the 90-day window bounds the size.

In-repo precedent: `app/exports/invoice_export.rb:22` streams CSV for the billing area.

## Components and interfaces

```mermaid
flowchart LR
  DeliveriesController --> DeliveryExport
  DeliveryExport --> DeliveryHistoryQuery
  DeliveryHistoryQuery --> deliveries
```

### DeliveryHistoryQuery (new, `app/queries/delivery_history_query.rb`)

- Responsibility: select a user's deliveries from the last 90 days, in keyset order.
- Inputs: a user ID, from `DeliveryExport`.
- Outputs: a lazily enumerated relation of deliveries, 1,000 rows per batch.
- Errors: none of its own; a database error propagates to the controller.
- Layer: data access

### DeliveryExport (new, `app/exports/delivery_export.rb`)

- Responsibility: stream the query's rows as a zipped CSV.
- Inputs: a user ID, from `DeliveriesController#export`.
- Outputs: an enumerator of zip chunks.
- Versioning: column order is the contract; a new column is appended, never inserted.
- Layer: presentation and data access

### DeliveriesController#export (`app/controllers/deliveries_controller.rb`)

- Responsibility: serve the export to the signed-in user.
- Inputs: an authenticated request.
- Outputs: a streamed `application/zip` response with `Content-Disposition: attachment`.
- Errors: unauthenticated requests get the controller's existing 401.
- Versioning: a new route; no existing route changes.

## Likely changes

- The export format may change later.

## Data ownership

| Store | Owning module |
| --- | --- |
| `deliveries` table | the `Delivery` model, unchanged; this plan only reads it |

## Test strategy

| Level | Risks covered |
| --- | --- |
| unit | The 90-day boundary in `spec/queries/delivery_history_query_spec.rb` |
| integration | Zipped CSV content in `spec/exports/delivery_export_spec.rb` |
| system | The 30-second threshold at 100,000 rows in `spec/perf/delivery_export_perf_spec.rb` |
| acceptance | The three ACs, each named in the coverage table |

Coverage target: 100% branch coverage of the query and the export.

## NFR coverage

| Ticket | NFR | Design element |
| --- | --- | --- |
| ABC-231 | NFR1 | Should be fast enough once streaming is in place |
| ABC-230 | NFR1 | untouched — this branch changes nothing about webhook signing |

## Rejected alternatives

**A background job emailing the file.** Rejected: the 90-day window keeps the export small
enough to serve synchronously, as GitHub does for archives.

## Phases

### Phase 1 — 90-day keyset query

- Files touched: `app/queries/delivery_history_query.rb` (new),
  `spec/queries/delivery_history_query_spec.rb` (new)
- Change summary: A query object returning a user's last 90 days of deliveries in keyset
  batches of 1,000.
- Tests added: the 90-day boundary and batch ordering.
- Commit message: `ABC-231 - Add a 90-day keyset delivery query`

### Phase 2 — Stream the zipped CSV

- Files touched: `Gemfile`, `Gemfile.lock`, `app/exports/delivery_export.rb` (new),
  `app/controllers/deliveries_controller.rb`, `spec/exports/delivery_export_spec.rb` (new),
  `spec/perf/delivery_export_perf_spec.rb` (new)
- Change summary: Add the `zip_kit` gem for streaming zip output. `DeliveryExport` writes
  CSV rows into a `zip_kit` streamer; the controller gains an `export` action returning it.
- Tests added: zipped CSV content, and the 100,000-row timing.
- Commit message: `ABC-231 - Stream delivery history as a zipped CSV`

## Risks and open questions

None.

## Ticket gaps

None.

---

# ABC-231 (ticket as written)

**Summary:** Download delivery history as a zipped CSV

**Description:**

Users reconciling webhook activity against their own systems need their delivery history
as a file. Heavy accounts produce large files, so the download is compressed.

**Acceptance Criteria:**

- A user can download their delivery history as a zipped CSV
- The export includes every delivery from the last 90 days

**Non-functional requirements:**

- NFR1: an export of 100,000 deliveries completes in under 30 seconds [verify: system @ spec/perf/delivery_export_perf_spec.rb]

**Parent Epic:** ABC-230 — Delivery history self-service

**Non-functional requirements:**

- NFR1: a webhook signature verifies in under 5 ms at p99 [verify: unit @ spec/signing/verify_spec.rb]
