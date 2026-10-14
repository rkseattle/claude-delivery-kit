# Draft format

`scripts/lint_draft.py` parses this format, so it is strict. One draft file holds every
ticket for one request, in build order.

## Header

```
# [S1] Reject expired refresh tokens on the refresh endpoint
Type: Story
Parent: E1
Blocked by: T1
Handoff: auth-refresh-pr-01
Priority: Must
Goal:
Labels:
Jira:
```

- **ID** — `E<n>`, `S<n>`, `T<n>`, `B<n>`; unique in the file. Replaced by the key on
  creation.
- **Summary** — imperative verb and object, one behavior, at most 100 characters.
- **Type** — `Epic`, `Story`, `Task`, or `Bug`.
- **Parent** — an epic's local ID or key. **Blocked by** — IDs or keys, or `None`.
- **Handoff** — the label `plan-work` will be run with. Required on Story, Task, and Bug;
  a handoff group stays within `plan-work`'s handoff limit, in build order.
- **Priority** — `Must`, `Should`, `Could`, or `Won't`, with a straight apostrophe
  (MoSCoW). Required on Story, Task, and Bug; optional on an Epic. `Won't` records work
  deliberately left out.
- **Goal** — one sentence naming the outcome the ticket serves. Required on a Story or
  Task with no `Parent:`; a child serves its epic's goal, and a Bug restores behavior a goal
  already justified.
- **Jira** — empty; filled on creation. **Open questions** — must be empty before review.

## Line formats

```
- AC1: <observable behavior, concrete values> [verify: <tier> @ <test path or session>]
- path/from/repo/root (modify|new|delete): <what changes>
- T1: <what it provides>                          (Dependencies)
- <key> (Done): <what it provides>                (Dependencies)
- Code: `symbol()` in path/to/file (exists on the parent branch)
- SM1: <observable measure> [children: S1, S2]    (Epic success measures)
- NFR1: <metric> <comparator> <number><unit> <condition> [verify: <tier> @ <evidence>]
```

Commas and semicolons inside an AC make separate `plan-work` rows. Use them only between
clauses that are each verifiable; keep lists of values inside backticks.

An NFR line's threshold is its first comparator — `<`, `<=`, `>`, `>=`, `=`, `≤`, or `≥`,
never a word — then a number and its unit: `p95 response < 300 ms at 200 requests/second`,
not `p95 stays low over 24 hours`. Numbers in the metric name or the condition do not
count. The linter checks the comparator and number; the unit is checked in review.

Touch points are production files only; tests appear as AC evidence. Dependencies with
none: `- None`.

## Sections by type

| Type  | Sections, in order |
| ----- | ------------------ |
| Epic  | Goal, Success measures, In scope, Out of scope, Children |
| Story | Context, Behavior, Acceptance criteria, Touch points, Out of scope, Dependencies |
| Task  | Context, Change, Acceptance criteria, Touch points, Out of scope, Dependencies |
| Bug   | Environment, Steps to reproduce, Expected, Actual, Evidence, Acceptance criteria, Touch points, Out of scope, Dependencies |

An Epic or a Story may add **Non-functional requirements**, after Success measures or
Behavior: one NFR line per quality threshold, in the format above.

Every type may add **Implementation notes** — constraints with a reason, never steps. A
design written there is a proposal `plan-work` checks against real implementations, not a
decision.

- **Context** — why the ticket exists; any linked source summarized in the ticket.
- **Behavior** — the one change, from the user's or caller's side.
- **Change** — the technical change and why it is needed.
- **Evidence** — log lines, stack trace, failing test name; root cause as `file:line`
  when known.
- **Out of scope** — each item with where it lives: a ticket, or `(not planned)`. An
  excluded instance of a root cause states why it is benign in context.

A spike Task has one AC: a decision record committed at a named path, stating the option
chosen and why.

## Example

```
# [S1] Rotate the refresh token on the refresh endpoint
Type: Story
Parent: E1
Blocked by: T1
Handoff: auth-refresh-pr-01
Priority: Must
Jira:

## Context
Access tokens expire after one hour (`ACCESS_TTL` in src/auth/config.ts). Users with
"Keep me signed in" need a 30-day session without re-entering credentials.

## Behavior
POST /auth/refresh with a valid `rt` cookie returns a new access token, sets a new `rt`,
and revokes the old one.

## Acceptance criteria
- AC1: POST /auth/refresh with a valid `rt` returns 200 with body `{ accessToken }` [verify: automated @ tests/auth/refresh.test.ts]
- AC2: The same request sets a new `rt` cookie with attributes `HttpOnly; Secure; SameSite=Strict` [verify: automated @ tests/auth/refresh.test.ts]
- AC3: The old token's row has `revoked_at` and `replaced_by` set after the request [verify: automated @ tests/auth/refresh.test.ts]

## Touch points
- src/auth/routes.ts (modify): register the refresh route
- src/auth/refresh.ts (new): rotation logic

## Out of scope
- Reuse detection for revoked tokens (S2)

## Dependencies
- T1: `refresh_tokens` table and repository functions
- Code: `signAccessToken()` in src/auth/tokens.ts (exists on the parent branch)
```
