<!-- expect JIRA=1 R15=4 -->
# [E1] Keep signed-in users signed in for 30 days
Type: Epic
Blocked by: None
Jira: AB-15

## Goal
Users who choose "Keep me signed in" stay signed in on that device for 30 days.

## Success measures
- SM1: A user who signed in 29 days ago gets a new access token without credentials [children: S1, S2]
- SM2: A revoked refresh token is rejected with 401 [children: S3, S4]

## In scope
- Refresh-token rotation for the web client

## Out of scope
- Mobile clients (not planned)

## Children
- S1, S2, S3, S4

# [S1] Rotate the refresh token on the refresh endpoint
Type: Story
Priority: Must
Parent: E1
Blocked by: None
Handoff: rewrite-pr-01
Jira: AB-12

## Context
Access tokens expire after one hour (`ACCESS_TTL` in src/auth/config.ts).

## Behavior
POST /auth/refresh with a valid `rt` cookie returns a new access token and sets a new `rt`.

## Acceptance criteria
- AC1: POST /auth/refresh with a valid `rt` returns 200 [verify: automated @ tests/auth/refresh.test.ts]
- AC2: The same request sets a new `rt` cookie with `HttpOnly` [verify: automated @ tests/auth/refresh.test.ts]

## Touch points
- src/auth/routes.ts (modify): register the refresh route

## Out of scope
- Reuse detection for revoked tokens (S3)

## Dependencies
- None

## Change impact
- AC2 changed: the cookie needed no attributes; now it is `HttpOnly`
- AB-13 scope: takes the 30-day expiry this ticket no longer covers

# [S2] Expire the session after 30 days
Type: Story
Priority: Should
Parent: E1
Blocked by: None
Handoff: rewrite-pr-01
Jira: AB-13

## Context
A refresh token older than 30 days must not mint an access token.

## Behavior
POST /auth/refresh with a 31-day-old `rt` returns 401.

## Acceptance criteria
- AC1: POST /auth/refresh with a 31-day-old `rt` returns 401 [verify: automated @ tests/auth/refresh.test.ts]

## Touch points
- src/auth/routes.ts (modify): age check

## Out of scope
- Mobile clients (not planned)

## Dependencies
- None

# [S3] Reject a revoked refresh token
Type: Story
Priority: Must
Parent: E1
Blocked by: None
Handoff: rewrite-pr-02
Jira: AB-14

## Context
A revoked token must not mint an access token.

## Behavior
POST /auth/refresh with a revoked `rt` returns 401.

## Acceptance criteria
- AC1: POST /auth/refresh with a revoked `rt` returns 401 [verify: automated @ tests/auth/refresh.test.ts]

## Touch points
- src/auth/routes.ts (modify): revocation check

## Out of scope
- Mobile clients (not planned)

## Dependencies
- None

## Change impact

# [S4] Sign out every device
Type: Story
Priority: Could
Parent: E1
Blocked by: None
Handoff: rewrite-pr-02
Jira:

## Context
A user who loses a device needs every session ended.

## Behavior
POST /auth/signout-all revokes every refresh token the user holds.

## Acceptance criteria
- AC1: POST /auth/signout-all returns 204 [verify: automated @ tests/auth/signin.test.ts]

## Touch points
- src/auth/routes.ts (modify): sign-out route

## Out of scope
- Mobile clients (not planned)

## Dependencies
- None

## Change impact
- AC1 added: sign-out returns 204
- AC2 removed: the List<String> of devices signed out
