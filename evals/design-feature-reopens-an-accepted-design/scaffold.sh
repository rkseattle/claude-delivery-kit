#!/usr/bin/env bash
# A git repo whose main holds an accepted design, merged from design/sms-appointment-reminders,
# and a gitignored write-tickets draft whose last review round marks ticket S2 for design
# rework, so design-feature's only path forward is reopen mode. The step 8 exceptions row
# and the agent rules are design-feature-stops-at-approval's, so the run reaches Step 5.
# origin is a local bare clone, so a fetch succeeds offline.
set -euo pipefail
git init -q
git symbolic-ref HEAD refs/heads/main
git config user.email eval@example.com
git config user.name eval
mkdir -p .claude/agent-rules docs/design docs/adr docs/tickets src/clinic tests
printf 'docs/tickets/\n' > .gitignore
cat > .claude/project.json <<'JSON'
{
  "ticket_prefix": "ABC",
  "jira_project": "ABC",
  "repo_slug": "owner/repo",
  "parent_branch_default": "main",
  "source_roots": "src tests",
  "build_command": "python3 -m unittest discover -s tests",
  "push_command": "git push -u --force-with-lease origin <branch>",
  "unit_test_scope": "the whole target",
  "post_fix_verification_scope": "everything",
  "verification_tiers": "ci · inspection",
  "brief_file": "none",
  "design_dir": "docs/design",
  "adr_dir": "docs/adr",
  "exceptions_log": "docs/exceptions-log.md",
  "project_size": "small",
  "lifecycle_model": "iterative",
  "disciplines": [],
  "roles": { "qa": "sam", "product_owner": "priya", "tech_lead": "lee" }
}
JSON
expiry=$(python3 -c 'import datetime; print(datetime.date.today() + datetime.timedelta(days=365))')
cat > docs/exceptions-log.md <<MD
| Rule | Reason | Risk | Expiry | Remediation |
| ---- | ------ | ---- | ------ | ----------- |
| Rule book Phase 3 step 8: design review by an engineer outside the immediate team, for designs | The clinic's team is its only engineers; no one outside it reviews designs | A design reaches its tickets with only the cold review behind it | $expiry | At expiry, renew, or name an outside reviewer |
MD
cat > .claude/agent-rules/feature-design-adversary.md <<'RULES'
# feature-design-adversary rules

- Web search and Jira are unavailable in this workspace. A survey source or Jira key that
  can only be checked there is UNVERIFIABLE, never a BLOCKER.
RULES
: > src/clinic/__init__.py
cat > src/clinic/appointments.py <<'PY'
"""Book, move, and cancel a clinic's appointments, held in memory."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Appointment:
    patient_name: str
    patient_phone: str
    clinician: str
    starts_at: datetime


class AppointmentBook:
    def __init__(self):
        self.appointments = {}
        self.next_id = 1

    def book(self, appointment):
        appointment_id = self.next_id
        self.appointments[appointment_id] = appointment
        self.next_id += 1
        return appointment_id

    def move(self, appointment_id, new_start):
        self.appointments[appointment_id].starts_at = new_start

    def cancel(self, appointment_id):
        del self.appointments[appointment_id]
PY
cat > tests/test_appointments.py <<'PY'
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from clinic.appointments import Appointment, AppointmentBook  # noqa: E402


class AppointmentBookTest(unittest.TestCase):
    def test_booking_returns_an_id(self):
        book = AppointmentBook()
        start = datetime(2026, 11, 2, 9, 0)
        self.assertEqual(book.book(Appointment("Ana", "+15550100", "Dr. Okafor", start)), 1)


if __name__ == "__main__":
    unittest.main()
PY
git add .gitignore .claude docs src tests
git commit -qm "Seed the appointment book and project configuration"
git switch -qc design/sms-appointment-reminders
cat > docs/design/sms-appointment-reminders.md <<'MD'
---
status: accepted
date: 2026-10-20
decision-makers: lee
---

# SMS appointment reminders

## Summary

Text each patient an SMS reminder 24 hours before their appointment, and again when the
appointment is moved or cancelled.

## Motivation

Missed appointments cost the clinic a slot each; patients ask for a reminder.

## Goals

- Patients get a reminder a day ahead and a notice when their appointment changes.

## Non-goals

- Two-way SMS replies; confirming by text is a later feature.

## Success measures

- SM1: Reminders sent for booked appointments: >= 95% by the first month live

## Current state

- `src/clinic/appointments.py:13` — `AppointmentBook` books, moves, and cancels in memory,
  with no hook for a change.

## Survey

- Twilio, "Send Appointment Reminders"
  (https://www.twilio.com/docs/messaging/tutorials/appointment-reminders): schedules the
  SMS when the appointment is created.
- RFC 5545, section 3.6.6 "Alarm Component": an alarm relative to the event's start moves
  with the event.

## Options

- Notify from `AppointmentBook` on each change through a `Notifier` — wins: the book is
  the one place appointments change.
- Poll for due appointments every minute — loses: a minute's lag, and a missed change.
- Do nothing — loses: no-shows continue.

## Proposal

Notify from `AppointmentBook` through a `Notifier` interface.

- Costly to reverse: send through Twilio's API — ADR: docs/adr/0001-send-sms-through-twilio.md

## Components and interfaces

```mermaid
flowchart LR
  staff[Clinic staff] --> app[Clinic app]
  app --> twilio[Twilio SMS]
```

```mermaid
flowchart LR
  book[AppointmentBook] --> notifier[Notifier]
```

### AppointmentBook — existing

- Responsibility: book, move, and cancel appointments
- Inputs: appointments and ids
- Outputs: appointment ids
- Errors: `KeyError` for an unknown id
- Versioning: none — in-process
- Layer: domain

### Notifier

- Responsibility: send one SMS per appointment event
- Inputs: an `Appointment` and an event kind
- Outputs: none
- Errors: `NotifierError` when Twilio refuses the message
- Versioning: none — in-process
- Layer: infrastructure

## Likely changes

- The message wording — `Notifier`

## Data model and ownership

- `Appointment` gains no fields.

| Dataset | Owner | Schema version location |
| ------- | ----- | ----------------------- |
| none — no dataset is added | — | — |

## Non-functional requirements

- NFR1: Reminder delivery latency <= 60 s — Notifier: sends at the reminder's due time

## Rollout and rollback

1. Enable the `Notifier` behind a setting — rollback: step 1's setting turned off.

## Observability

- A log line per SMS sent or refused.

## Test strategy

| Level | What | Where |
| ----- | ---- | ----- |
| Unit | Each event sends one SMS | `tests/test_notifier.py` |

Coverage target: every `Notifier` branch.

## Drawbacks

- Each SMS costs money.

## Risks

- Twilio outage — mitigation: refused messages are logged for staff to call.

## Work plan

### Handoff: sms-reminders-01

Delivers: SM1
Estimated changed lines: 300

- Add a Notifier interface and its Twilio implementation
  - Phase 1 — Notifier interface
  - Phase 2 — Twilio implementation
- Notify on book, move, and cancel
  - Phase 1 — AppointmentBook calls the Notifier

## Open questions

none — every choice is settled

## Decision

Approved by sam; priya; lee on 2026-10-20.
MD
cat > docs/adr/0001-send-sms-through-twilio.md <<'MD'
---
status: accepted
date: 2026-10-20
decision-makers: lee
---

# Send SMS through Twilio

## Context and Problem Statement

The clinic needs to send SMS.

## Considered Options

- Twilio
- AWS SNS

## Decision Outcome

Chosen option: Twilio, for its scheduling API.

### Consequences

- Good, because scheduling is built in.
- Bad, because the clinic depends on one vendor.
MD
git add docs/design docs/adr
git commit -qm "Record the SMS appointment reminders design and the tech lead's decision"
git switch -q main
git merge -q --no-ff -m "Merge the SMS appointment reminders design" design/sms-appointment-reminders
blob=$(git rev-parse HEAD:docs/design/sms-appointment-reminders.md)
cat > docs/tickets/sms-appointment-reminders.md <<MD
# [E1] SMS appointment reminders
Type: Epic
Jira:

## Goal
Patients get a reminder a day ahead and a notice when their appointment changes.

## In scope
- Design: \`docs/design/sms-appointment-reminders.md\`

# [S2] Notify on book, move, and cancel
Type: Story
Handoff: sms-reminders-01
Jira:

<!-- review round 3 -->
## S2 — NOT PLANNABLE
### BLOCKER
- NFR1's "<= 60 s" assumes a scheduler that sends at the due time, but the design names no
  scheduler: AppointmentBook only calls the Notifier on a change — design NFR1 — name the
  component that fires the 24-hour reminder
<!-- design-rework: S2 @ $blob -->
MD
git clone -q --bare . .git/origin.git
git remote add origin "$PWD/.git/origin.git"
git fetch -q origin
