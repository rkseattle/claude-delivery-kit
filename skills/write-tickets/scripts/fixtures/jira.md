<!-- expect JIRA=33 -->
# [S1] Export contacts as a file
Type: Story
Handoff: jira-pr-01
Priority: Must
Goal: Users keep a copy [offline].
Jira:

## Context
- [ ] A task box loses its box
The helper snake_case_name gains emphasis.
Bold **export** gains escapes.
A tag quoting code [verify: inspection @ the `max_age` review] loses its brackets.
The values x^2 and y^3 pair as superscript.
It takes ~30 to ~45 days.
Ask the owner ?? before shipping ??.
A !warning! reads as an image.
A !logo.png|width=40! reads as an image too.
The {{name}} placeholder reads as code.
A body `{ "error": "x" }` loses its closing brace.
Columns a||b read as a header.
bq. reads as a quote
h2. reads as a heading
* reads back as a dash bullet
See [the snake_case_name guide](https://example.com/guide) for details.

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

# [S2] Keep the export file name
Type: Story
Handoff: jira-pr-02
Priority: Must
Goal: Users keep the name they chose.
Jira:

## Context
Plain C++ yields HTML on the read.
Then every line is escaped, so lint_draft.py changes too.

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

# [S3] Name the export file
Type: Story
Handoff: jira-pr-03
Priority: Must
Goal: Users find the file by its date.
Jira:

## Context
Safe: `snake_case_name`, `C++`, `[200, 404]`, `a||b`, `!warning!` and lint_draft.py.
A lone x^2, a lone ~30, a lone ?? and a*b survive.
See [the guide](https://example.com/guide).
```
[ERROR] TBD handler failed fast in /app/pkg/__init__.py
```

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

# [S4] Open the export as a block
Type: Story
Handoff: jira-pr-04
Priority: Must
Goal: Users read the export inline.
Jira:

## Context
A `{code}` span opens a block that a later {code} closes.
```
fenced
```

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

# [S5] Render the country picker
Type: Story
Handoff: jira-pr-05
Priority: Must
Goal: Users pick a country from a list.
Jira:

## Context
The form renders a <select> element.
Return List<String> from the method.
See <https://example.com> for the spec.
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

# [S6] Lay out the export summary
Type: Story
Handoff: jira-pr-06
Priority: Must
Goal: Users read a summary of the export.
Jira:

## Context
> A quoted note survives.
---
| field | value |
|---|---|
| rows | 2 |
The old ~~flag~~ is struck.
```python
rows = 2
```
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

# [B1] Return 400 on an empty export
Type: Bug
Handoff: jira-pr-01
Priority: Should
Severity: High
Jira:

## Environment
Parent branch at the current commit.

## Steps to reproduce
1. POST /contacts/export with an empty body

## Expected
400 with `error` set to `empty`

## Actual
500

## Evidence
```
[ERROR] TBD handler failed fast in /app/pkg/__init__.py
```

## Acceptance criteria
- AC1: Regression: POST /contacts/export with an empty body returns 400 [verify: automated @ tests/auth/export.test.ts]

## Touch points
- src/auth/routes.ts (modify): validate the body

## Out of scope
- Import (not planned)

## Dependencies
- None
