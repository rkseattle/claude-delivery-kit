<!-- expect errors=3 warnings=1 -->
# [S1] Set the refresh cookie on sign-in
Type: Story
Handoff: auth-pr-01
Jira:

## Context
Sign-in returns only an access token today.

## Behavior
Sign-in with "Keep me signed in" sets an `rt` cookie.

## Acceptance criteria
- AC1: Sign-in returns 200, sets `rt`, and logs the event; audit row written [verify: automated @ tests/auth/signin.test.ts]
- AC2: Cookie attributes are `HttpOnly, Secure, SameSite=Strict` [verify: automated @ tests/auth/signin.test.ts]
- AC3: Works on the device lab phones [verify: out-of-band @ device lab session]
- AC4: Token stored hashed [verify: automated @ tests/missing/dir/hash.test.ts]
- AC5 Token expires after 30 days

## Touch points
- src/auth/routes.ts (modify): set cookie
- src/auth/config.ts: missing kind

## Out of scope
- Refresh endpoint (not planned)

## Dependencies
- None
