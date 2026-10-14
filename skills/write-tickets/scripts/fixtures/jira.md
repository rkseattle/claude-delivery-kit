<!-- expect errors=5 warnings=0 -->
# [S1] Export contacts as a file
Type: Story
Handoff: jira-pr-01
Priority: Must
Goal: Users keep a copy [offline].
Jira:

## Context
- [ ] A task box Jira drops
The helper snake_case_name breaks on the round trip.
Bold **export** breaks too.
A tag quoting code [verify: inspection @ the `max_age` review] cannot be wrapped.
Safe: `snake_case_name`, `[200, 404]`, [docs](https://example.com), lint_draft.py, a*b.

## Behavior
POST /contacts/export returns the file.

## Acceptance criteria
- AC1: POST /contacts/export returns 200 [verify: automated @ tests/auth/export.test.ts]

## Touch points
- src/auth/routes.ts (modify): export route

## Out of scope
- Import (not planned)

## Dependencies
- None
