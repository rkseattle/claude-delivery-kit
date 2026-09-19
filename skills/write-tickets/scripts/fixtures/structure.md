<!-- expect errors=15 warnings=0 -->
# [E1] Contacts export
Type: Epic
Blocked by: None
Jira:

## Goal
Users can take their contacts elsewhere.

## Success measures
- SM1: A user downloads their contacts [children: S1, S9]

## In scope
- Export

## Out of scope
- Import (not planned)

## Children
- S1, S2, S3, S4

# [S1] Download contacts as a file
Type: Story
Parent: E1
Blocked by: S4
Handoff: contacts-pr-01
Jira:
## Context
x
## Behavior
x
## Acceptance criteria
- AC1: Returns 200 [verify: automated @ tests/auth/export.test.ts]
## Touch points
- src/auth/routes.ts (modify): route
## Out of scope
- Import (not planned)
## Dependencies
- None

# [S2] Show a download button
Type: Story
Parent: E1
Blocked by: None
Handoff: contacts-pr-01
Jira:
## Context
x
## Behavior
x
## Acceptance criteria
- AC1: Button renders [verify: automated @ tests/auth/button.test.ts]
## Touch points
- src/auth/routes.ts (new): wrongly marked new
## Out of scope
- None (not planned)
## Dependencies
- None

# [S3] Log exports
Type: Story
Parent: E1
Handoff: contacts-pr-01
Jira:
## Context
x

# [S4] Rate-limit exports
Type: Story
Parent: E1
Blocked by: S1, bogus
Handoff: contacts-pr-01
Jira:
## Context
x
## Behavior
x
## Acceptance criteria
- AC1: The 11th request in a minute returns 429 [verify: automated @ tests/auth/limit.test.ts]
## Touch points
- src/auth/limiter.ts (modify): missing file
## Out of scope
- None (not planned)
## Dependencies
- None

# [B1] Fix crash on empty export
Type: Bug
Handoff: contacts-pr-02
Jira:
## Environment
x
## Steps to reproduce
1. x
## Expected
x
## Actual
x
## Evidence
x
## Acceptance criteria
- AC1: Empty list returns 200 [verify: automated @ tests/auth/empty.test.ts]
## Touch points
- src/auth/routes.ts (modify): guard
## Out of scope
- None (not planned)
## Dependencies
- None
