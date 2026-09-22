---
description: An acceptance criterion with no phase is a BLOCKER; narrowing the definition did not blind the reviewer
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
fetched them yourself. The repository the plan describes is not present either, so treat
the plan's factual claims about existing code as verified — you cannot grep for what is
not here, and a claim you cannot check is `UNVERIFIABLE`, not a `BLOCKER`.

Return findings in the format the agent definition specifies.

---

# ABC-207 — Let users export their delivery history

## Scope

What ships: a CSV export of a user's webhook delivery history, generated on request and
downloaded from the delivery history view.

What explicitly does not ship: JSON export. The ticket asks for CSV only.

Covering ticket: ABC-207.

## Acceptance criteria coverage

| ID | Ticket | AC | Phase | Verified by | Deviation |
| --- | --- | --- | --- | --- | --- |
| AC1 | ABC-207 | A user can export their delivery history as CSV | 2 | `spec/exports/delivery_export_spec.rb:generates_csv` | — |
| AC2 | ABC-207 | The export includes every delivery from the last 90 days | 1 | `spec/exports/delivery_export_spec.rb:covers_90_days` | — |
| AC3 | ABC-207 | The export column order matches the on-screen table | 2 | `spec/exports/delivery_export_spec.rb:column_order` | — |

## Approach

Streaming CSV generation via Ruby's built-in `CSV` library, written to the response as it
is produced rather than assembled in memory. This is the standard approach for exports of
unbounded size and is what Rails' own guides describe for `send_data` with a streaming
body.

In-repo precedent: `app/exports/invoice_export.rb:22` streams CSV the same way for the
billing area, including the same `Content-Disposition` handling.

## Rejected alternatives

**Assembling the CSV in memory and sending it in one write.** Simpler, and rejected: a
heavy account's 90-day history is large enough to matter, and the streaming version is
already implemented next door in `invoice_export.rb`.

**A background job emailing the file.** Rejected as heavier than the ticket needs; the
export is small enough to serve synchronously.

## Phases

### Phase 1 — Add the 90-day delivery history query

- Files touched: `app/queries/delivery_history_query.rb` (new),
  `spec/queries/delivery_history_query_spec.rb` (new)
- Change summary: A query object returning a user's deliveries from the last 90 days,
  ordered to match the on-screen table. Uses the existing index on
  `deliveries(user_id, created_at)`.
- Tests added: coverage of the 90-day boundary and the ordering.
- Commit message: `ABC-207 - Add 90-day delivery history query`

### Phase 2 — Stream the history as CSV from the export endpoint

- Files touched: `app/exports/delivery_export.rb` (new),
  `app/controllers/deliveries_controller.rb`,
  `spec/exports/delivery_export_spec.rb` (new)
- Change summary: A `DeliveryExport` streaming the query's rows as CSV, following
  `invoice_export.rb`. The controller gains an `export` action returning it with the
  appropriate `Content-Disposition`.
- Tests added: CSV generation, column order matching the on-screen table, and the 90-day
  window end to end.
- Commit message: `ABC-207 - Stream delivery history as CSV`

## Risks and open questions

None.

## Ticket gaps

None.

---

# ABC-207 (ticket as written)

**Summary:** Let users export their delivery history

**Description:**

Users reconciling webhook activity against their own systems currently have to page
through the delivery history view by hand. They should be able to export it.

**Acceptance Criteria:**

- A user can export their delivery history as CSV
- The export includes every delivery from the last 90 days
- The export column order matches the on-screen table
- Exporting is rate limited to once per minute per user
