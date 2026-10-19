<!-- expect R3=1 R7=4 -->
# [S1] Rotate the refresh token on the refresh endpoint
Type: Story
Priority: Must
Goal: Users stay signed in across browser restarts.
Handoff: auth-paths-pr-01
Jira:

## Context
Evidence and touch points are resolved against what git tracks, not what is on disk.

## Behavior
The refresh endpoint issues a new refresh token and revokes the old one.

## Acceptance criteria
- AC1: The old token is revoked on refresh [verify: automated @ tests/auth/untracked.test.ts]
- AC2: The new token is returned once [verify: automated @ Tests/auth/login.test.ts]
- AC3: A reused token is rejected with 401 [verify: automated @ ../outside/reuse.test.ts]
- AC4: The rotation is logged [verify: automated @ tests/auth/refresh.test.ts]
- AC5: The rotation is audited [verify: automated @ ./tests/auth/login.test.ts]

## Touch points
- src/auth/untracked.ts (modify): rotate on refresh
- tests/auth/untracked.test.ts (new): rotation tests
- src/auth (modify): the module directory
- src/auth/ (modify): the module directory, written with its slash

## Out of scope
- Mobile clients (not planned)

## Dependencies
- None
