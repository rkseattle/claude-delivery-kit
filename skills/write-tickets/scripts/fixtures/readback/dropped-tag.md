<!-- expect id=S1 missing=1 -->
Goal: Users stay signed in for 30 days.

## Context

Access tokens expire after one hour (`ACCESS_TTL`).

## Behavior

POST /auth/refresh with a valid `rt` cookie returns a new access token.

## Non-functional requirements

- NFR1: p95 response < 300 ms at 200 requests/second `[verify: automated @ tests/auth/refresh.test.ts]`

## Acceptance criteria

- AC1: POST /auth/refresh returns 200
- AC2: The old row has `revoked_at` set `[verify: automated @ tests/auth/refresh.test.ts]`
- AC3: The response body quotes `[verify:]` beside `max_age` `[verify: inspection @ refresh contract review]`

## Touch points

- src/auth/routes.ts (modify): register the route

## Out of scope

- Reuse detection (not planned)

## Dependencies

- None
