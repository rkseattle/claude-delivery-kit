<!-- expect FORMAT=2 JIRA=1 R15=4 -->
# [AB-15] Keep signed-in users signed in for 30 days
Type: Epic
Blocked by: None
Baseline: AB-15
Jira: AB-15

## Goal
Users who choose "Keep me signed in" stay signed in on that device for 30 days.

## Success measures
- SM1: A user who signed in 29 days ago gets a new access token without credentials [children: AB-12, AB-13]
- SM2: A revoked refresh token is rejected with 401 [children: AB-14, S4]

## In scope
- Refresh-token rotation for the web client

## Out of scope
- Mobile clients (not planned)

## Children
- AB-12, AB-13, AB-14, S4

# [AB-12] Rotate the refresh token on the refresh endpoint
Type: Story
Priority: Must
Parent: AB-15
Blocked by: None
Handoff: rewrite-pr-01
Baseline: AB-12
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
- Reuse detection for revoked tokens (AB-14)

## Dependencies
- None

## Change impact
- AC2 changed: the cookie needed no attributes; now it is `HttpOnly`
- AB-13 scope: takes the 30-day expiry this ticket no longer covers

# [AB-13] Expire the session after 30 days
Type: Story
Priority: Should
Parent: AB-15
Blocked by: None
Handoff: rewrite-pr-01
Baseline: AB-13
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

# [AB-14] Reject a revoked refresh token
Type: Story
Priority: Must
Parent: AB-15
Blocked by: None
Handoff: rewrite-pr-02
Baseline: AB-14
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
Parent: AB-15
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

# [AB-16] Let users see where they are signed in
Type: Epic
Blocked by: None
Baseline: AB-16
Jira: AB-16

## Goal
Users can see each device where they are signed in.

## Success measures
- SM1: A user lists the devices holding a refresh token [children: AB-17, AB-19, S5]

## In scope
- The web client

## Out of scope
- Mobile clients (not planned)

## Children
- AB-17, AB-19, S5

## Change impact
- SM1 changed: listed `AB-13`; now lists `AB-17`, `AB-19`, `S5`
- SM2 removed: a user signs out one device; now part of sign-out
- SM3 removed: the List<String> of devices signed out

# [AB-17] List the devices a user is signed in on
Type: Story
Priority: Could
Parent: AB-16
Blocked by: None
Handoff: rewrite-pr-03
Jira: AB-17

## Context
Step 8 created this ticket in this run, so it has a key and no baseline.

## Behavior
GET /auth/devices returns each device holding a refresh token.

## Acceptance criteria
- AC1: GET /auth/devices returns 200 [verify: automated @ tests/auth/signin.test.ts]

## Touch points
- src/auth/routes.ts (modify): devices route

## Out of scope
- Mobile clients (not planned)

## Dependencies
- None

# [AB-19] Name each signed-in device
Type: Story
Priority: Could
Parent: AB-16
Blocked by: None
Handoff: rewrite-pr-03
Baseline: AB-18
Jira: AB-19

## Context
A rewrite whose Baseline: names a different issue than its Jira: line.

## Behavior
GET /auth/devices returns a name for each device.

## Acceptance criteria
- AC1: GET /auth/devices returns 200 [verify: automated @ tests/auth/signin.test.ts]

## Touch points
- src/auth/routes.ts (modify): devices route

## Out of scope
- Mobile clients (not planned)

## Dependencies
- None

## Change impact
- AC1 changed: returned 204; now returns 200

# [S5] Rename a signed-in device
Type: Story
Priority: Could
Parent: AB-16
Blocked by: None
Handoff: rewrite-pr-04
Baseline: AB-20
Jira:

## Context
A rewrite whose Baseline: is filled and whose Jira: line is empty.

## Behavior
PATCH /auth/devices/1 sets the device name.

## Acceptance criteria
- AC1: PATCH /auth/devices/1 returns 200 [verify: automated @ tests/auth/signin.test.ts]

## Touch points
- src/auth/routes.ts (modify): rename route

## Out of scope
- Mobile clients (not planned)

## Dependencies
- None

## Change impact
- AC1 added: renaming returns 200
