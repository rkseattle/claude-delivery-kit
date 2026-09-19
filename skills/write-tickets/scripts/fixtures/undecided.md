<!-- expect errors=7 warnings=3 -->
# [S1] Export and import contacts
Type: Story
Handoff: contacts-pr-01
Jira:

## Context
As discussed, users want this.

## Behavior
Users can export contacts, e.g. as CSV, and errors are handled gracefully.

## Acceptance criteria
- AC1: Export works TBD
- AC2: Import is fast [verify: automated @ tests/contacts/import.test.ts]

## Touch points
- src/contacts/export.ts (modify): add export

## Out of scope

## Dependencies
- None

## Open questions
- Which format?
