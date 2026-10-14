# [E1] Keep users signed in
Type: Epic
Blocked by: None
Jira:

## Goal
Users stay signed in for 30 days.

## Success measures
- SM1: A 29-day-old session refreshes without credentials [children: S1]

## In scope
- The web client

## Out of scope
- Mobile clients (not planned)

## Children
- S1

# [S1] Rotate the refresh token on refresh
Type: Story
Blocked by: None
Handoff: auth-pr-01
Priority: Must
Goal: Users stay signed in for 30 days.
Jira:

## Context
Access tokens expire after one hour (`ACCESS_TTL`).
1. Sign in
2. Wait an hour

## Behavior
POST /auth/refresh with a valid `rt` cookie returns a new access token.

## Non-functional requirements
- NFR1: p95 response < 300 ms at 200 requests/second [verify: automated @ tests/auth/refresh.test.ts]

## Acceptance criteria
- AC1: POST /auth/refresh returns 200 [verify: automated @ tests/auth/refresh.test.ts]
- AC2: The old row has `revoked_at` set [verify: automated @ tests/auth/refresh.test.ts]
- AC3: The response body quotes `[verify:]` beside `max_age` [verify: inspection @ refresh contract review]

## Touch points
- src/auth/routes.ts (modify): register the route
- `src/auth/__init__.py` (modify): export the route

## Out of scope
- Reuse detection (AB-5)

## Dependencies
- AB-4: `refresh_tokens` table

## Open questions

# [T9] Connector probe
Type: Task
Jira:

## Probe
- P1: bare tag [verify: inspection @ skills/write-tickets/SKILL.md]
- P2: code-span tag `[verify: inspection @ skills/write-tickets/SKILL.md]`
- P5: p95 response < 300 ms at 200 requests/second, availability >= 99.9%, Login->dashboard
- P8: link [docs](https://example.com) and value list `[200, 404]` and quoted `[R14]`
- P10: ampersand & less-than < and pipe | and hash # inline
A hard-wrapped paragraph whose first line ends here
and whose second line continues it.
1. Numbered one
2. Numbered two
