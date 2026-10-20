---
description: An NFR with no NFR coverage row is a BLOCKER even when a phase delivers it, and so is an affected Epic NFR with no phase
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
fetched them yourself. The ticket's parent Epic, ABC-218, is reproduced after it. The
repository the plan describes is not present either, so treat the plan's factual claims
about existing code as verified — you cannot grep for what is not here, and a claim you
cannot check is `UNVERIFIABLE`, not a `BLOCKER`.

Return findings in the format the agent definition specifies.

---

# ABC-219 — Paginate the delivery history API

## Scope

What ships: cursor pagination on `GET /api/deliveries`, which today returns a user's whole
delivery history in one response.

What explicitly does not ship: pagination of the delivery history view. It already pages
server-side through `DeliveriesController#index`, and the ticket covers the API only.

Covering ticket: ABC-219.

## Acceptance criteria coverage

| ID | Ticket | AC | Phase | Verified by | Deviation |
| --- | --- | --- | --- | --- | --- |
| AC1 | ABC-219 | A request with no cursor returns the newest page | 2 | `spec/requests/api/deliveries_spec.rb:first_page` | — |
| AC2 | ABC-219 | A response with more results carries a `next_cursor` | 2 | `spec/requests/api/deliveries_spec.rb:next_cursor` | — |
| AC3 | ABC-219 | A request with `next_cursor` returns the following page with no gaps or repeats | 1 | `spec/queries/delivery_page_query_spec.rb:no_gaps_or_repeats` | — |
| AC4 | ABC-219 | NFR1: p95 response under 300 ms at 200 requests/second | 2 | `spec/perf/deliveries_api_load_spec.rb:p95_under_300ms` | — |
| AC5 | ABC-219 | NFR2: response body at most 256 KB per page | 2 | `spec/requests/api/deliveries_spec.rb:page_body_under_256kb` | — |

## Approach

Surveyed: Stripe's list API (`starting_after` with an opaque object ID), Slack's Web API
(`cursor` and `next_cursor` in `response_metadata`), and GitHub's REST API (`Link` headers,
cursor-based on its newer endpoints) all page large, append-mostly collections with an
opaque cursor rather than an offset, because an offset skips or repeats rows when new rows
arrive between requests. This plan follows Slack's shape — `next_cursor` in the body — with
keyset pagination underneath: the cursor encodes the last row's `(created_at, id)`, and the
next page is the rows strictly after it in index order.

In-repo precedent: `app/queries/invoice_page_query.rb:12` already pages invoices by keyset
on `(created_at, id)` with a Base64 cursor. This plan follows it.

## Components and interfaces

```mermaid
flowchart LR
  Api::DeliveriesController --> DeliveryPageQuery
  DeliveryPageQuery --> deliveries
```

### DeliveryPageQuery (new, `app/queries/delivery_page_query.rb`)

- Responsibility: return one page of a user's deliveries after a keyset cursor.
- Inputs: a user ID, an optional decoded cursor, and a page size of at most 100.
- Outputs: the page's rows and the cursor of its last row, or `nil` when no rows remain.
- Errors: raises `InvalidCursor` on a cursor that does not decode.
- Versioning: the cursor is opaque to clients, so its encoding can change; keyword
  arguments for later filters.
- Layer: data access

### Api::DeliveriesController#index (`app/controllers/api/deliveries_controller.rb`)

- Responsibility: serve one page as JSON.
- Inputs: an authenticated request with optional `cursor` and `limit`.
- Outputs: `{ "deliveries": [...], "next_cursor": "..." }`.
- Errors: `InvalidCursor` becomes a 400; a `limit` above 100 is clamped to 100.
- Versioning: breaking for clients that read the whole history in one response; the API
  changelog announces it, and those clients follow `next_cursor` to read the rest.
- Layer: presentation

## Likely changes

- The cursor encoding — hidden behind `DeliveryPageQuery`.

## Data ownership

| Store | Owning module |
| --- | --- |
| `deliveries` table | the `Delivery` model, unchanged; this plan only reads it |

## Test strategy

| Level | Risks covered |
| --- | --- |
| unit | Cursor decoding and the no-gaps, no-repeats property in `spec/queries/delivery_page_query_spec.rb` |
| integration | Response shape, `next_cursor`, the 400, and the body size in `spec/requests/api/deliveries_spec.rb` |
| system | p95 latency at 200 requests/second in `spec/perf/deliveries_api_load_spec.rb` |
| acceptance | The five ACs, each named in the coverage table |

Coverage target: 100% branch coverage of the query and the controller action.

## NFR coverage

| Ticket | NFR | Design element |
| --- | --- | --- |
| ABC-219 | NFR1 | `DeliveryPageQuery`: a keyset query on the existing `deliveries(user_id, created_at, id)` index, so a page reads at most `limit` rows from the index |
| ABC-218 | NFR2 | `Api::DeliveriesController#index`: clamping `limit` to 100 caps the rows serialized per request |

## Rejected alternatives

**Offset pagination.** Simplest, and rejected: deliveries arrive continuously, so an offset
skips or repeats rows between requests, which AC3 forbids.

**`Link` headers, as GitHub does.** Rejected: the API's existing clients read the body,
and Slack's in-body cursor needs no header parsing.

## Phases

### Phase 1 — Keyset page query

- Files touched: `app/queries/delivery_page_query.rb` (new),
  `spec/queries/delivery_page_query_spec.rb` (new)
- Change summary: A query object returning one page after a cursor, ordered and filtered
  by `(created_at, id)` to use the existing index. Follows `invoice_page_query.rb`.
- Tests added: cursor round trip, and no gaps or repeats across inserts between pages.
- Commit message: `ABC-219 - Add a keyset page query for deliveries`

### Phase 2 — Paginate the API endpoint

- Files touched: `app/controllers/api/deliveries_controller.rb`,
  `spec/requests/api/deliveries_spec.rb`, `spec/perf/deliveries_api_load_spec.rb` (new),
  `docs/api/changelog.md`
- Change summary: `index` reads `cursor` and `limit`, clamps `limit` to 100, returns the
  page with `next_cursor`, and maps `InvalidCursor` to a 400. Changelog entry added.
- Tests added: first page, `next_cursor`, the 400, a full 100-row page's body size, and
  the p95 load spec against the paginated endpoint.
- Commit message: `ABC-219 - Paginate the delivery history API`

## Risks and open questions

None.

## Ticket gaps

None.

---

# ABC-219 (ticket as written)

**Summary:** Paginate the delivery history API

**Description:**

`GET /api/deliveries` returns a user's whole delivery history in one response. Heavy
accounts time out, and clients cannot resume a partial read.

**Acceptance Criteria:**

- A request with no cursor returns the newest page
- A response with more results carries a `next_cursor`
- A request with `next_cursor` returns the following page with no gaps or repeats

**Non-functional requirements:**

- NFR1: p95 response under 300 ms at 200 requests/second [verify: system @ spec/perf/deliveries_api_load_spec.rb]
- NFR2: response body at most 256 KB per page [verify: integration @ spec/requests/api/deliveries_spec.rb]

**Parent Epic:** ABC-218 — Public API reliability

**Non-functional requirements:**

- NFR1: API 5xx error rate below 0.1% of requests over 7 days [verify: system @ the API error-rate dashboard]
- NFR2: API p99 response under 1 second for any list endpoint [verify: system @ spec/perf/api_list_endpoints_spec.rb]
