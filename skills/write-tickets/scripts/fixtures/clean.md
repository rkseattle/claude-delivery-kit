<!-- expect errors=0 warnings=0 -->
# [E1] Keep signed-in users signed in for 30 days
Type: Epic
Blocked by: None
Jira:

## Goal
Users who choose "Keep me signed in" stay signed in on that device for 30 days.

## Success measures
- SM1: A user who signed in 29 days ago gets a new access token without credentials [children: T1, S1]
- SM2: A revoked refresh token is rejected with 401 [children: S2]

## In scope
- Refresh-token issuance and rotation for the web client

## Out of scope
- Mobile clients (not planned)

## Children
- T1, S1, S2

# [T1] Create the refresh_tokens table with repository functions
Type: Task
Parent: E1
Blocked by: AB-12
Handoff: auth-refresh-pr-01
Labels: enabling
Jira:

## Context
S1 and S2 store refresh tokens server-side; no table exists for them.

## Change
Add table `refresh_tokens` and a repository module exposing `insert`, `findByHash`, `revoke`.

## Acceptance criteria
- AC1: Migrating an empty database creates `refresh_tokens` with a unique index on `token_hash` [verify: automated @ tests/auth/tokens-table.test.ts]

## Touch points
- src/auth/tokenStore.ts (new): repository functions

## Out of scope
- Rotation logic (S1)

## Dependencies
- AB-12 (Done): migration runner

# [S1] Rotate the refresh token on the refresh endpoint
Type: Story
Parent: E1
Blocked by: T1
Handoff: auth-refresh-pr-01
Jira:

## Context
Access tokens expire after one hour (`ACCESS_TTL` in src/auth/config.ts).

## Behavior
POST /auth/refresh with a valid `rt` cookie returns a new access token and replaces the cookie.

## Acceptance criteria
- AC1: POST /auth/refresh with a valid `rt` returns 200 with body `{ accessToken }` [verify: automated @ tests/auth/refresh.test.ts]
- AC2: The old token row has `revoked_at` set after the request [verify: automated @ tests/auth/refresh.test.ts]

## Touch points
- src/auth/routes.ts (modify): register the route
- src/auth/tokenStore.ts (modify): add `markReplaced`

## Out of scope
- Reuse detection (S2)

## Dependencies
- T1: `refresh_tokens` table
- Code: `signAccessToken()` in src/auth/tokens.ts (exists on the parent branch)

# [S2] Reject a revoked refresh token with 401
Type: Story
Parent: E1
Blocked by: S1
Handoff: auth-refresh-pr-02
Jira:

## Context
Rotation makes each refresh token single-use.

## Behavior
POST /auth/refresh with a revoked token returns 401.

## Acceptance criteria
- AC1: POST /auth/refresh with a revoked `rt` returns 401 with body `{ "error": "refresh_reused" }` [verify: automated @ tests/auth/refresh.test.ts]
- AC2: A signed-in session on a second device stays usable after AC1 [verify: out-of-band @ two-device sign-in session]

## Touch points
- src/auth/routes.ts (modify): reuse branch

## Out of scope
- Email notification (not planned)

## Dependencies
- S1: rotation marks used tokens

# [B1] Return 400 when the login email is empty
Type: Bug
Blocked by: None
Handoff: auth-refresh-pr-02
Jira:

## Environment
Parent branch at the current commit; local dev server.

## Steps to reproduce
1. POST /auth/login with body `{ "email": "", "password": "x" }`

## Expected
400 with body `{ "error": "email_required" }`

## Actual
500 with an unhandled exception

## Evidence
Unhandled rejection in src/auth/routes.ts when `email` is empty.

## Acceptance criteria
- AC1: Regression: POST /auth/login with an empty email returns 400 with body `{ "error": "email_required" }` [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): validate `email` before lookup

## Out of scope
- Password strength rules (not planned)

## Dependencies
- None
