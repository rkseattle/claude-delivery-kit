#!/usr/bin/env bash
# A git repo with one commit on main: a project.json naming design_dir and adr_dir, a small
# appointment module for Current state to inventory, and an exceptions log whose step 8 row
# lets a design with no outside reviewer pass, so the only stop left for design-feature is
# the approvals. origin is a local bare clone, so a fetch succeeds offline.
set -euo pipefail
# Each case's scaffold runs alone in its own workspace, so this setup is repeated from
# plan-project-stops-at-approval's rather than sourced from a file outside the case.
git init -q
# The harness may have run git init already, which ignores -b; name the branch directly.
git symbolic-ref HEAD refs/heads/main
git config user.email eval@example.com
git config user.name eval
# docs/design and docs/adr exist so a compliant run writes there without a mkdir; git
# ignores them empty.
mkdir -p .claude/agent-rules docs/design docs/adr src/clinic tests
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
# Computed at scaffold time so the row never expires under the case.
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
cat > src/clinic/__init__.py <<'PY'
PY
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
        if any(existing.clinician == appointment.clinician
               and existing.starts_at == appointment.starts_at
               for existing in self.appointments.values()):
            raise ValueError("clinician already booked at that time")
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
    def test_double_booking_a_clinician_is_refused(self):
        book = AppointmentBook()
        start = datetime(2026, 11, 2, 9, 0)
        book.book(Appointment("Ana", "+15550100", "Dr. Okafor", start))
        with self.assertRaises(ValueError):
            book.book(Appointment("Ben", "+15550101", "Dr. Okafor", start))


if __name__ == "__main__":
    unittest.main()
PY
git add .claude docs src tests
git commit -qm "Seed the appointment book and project configuration"
git clone -q --bare . .git/origin.git
git remote add origin "$PWD/.git/origin.git"
git fetch -q origin
