#!/usr/bin/env python3
"""Incident-review checks, so the skill settles none of them by eye. Standard library only.

Called by skills/incident-review/SKILL.md (Step 1).

    incident_check.py working-days --incident YYYY-MM-DD --start YYYY-MM-DD
        `<n>\ton time`, or `<n>\tlate` when n, the working days after the incident up to and
        including the start, is more than five
    incident_check.py slug [--title WORDS]
        the review's <slug> for the words, or standard input: project_rules.slug_of fitted
        to SLUG_MAX; INVALID when no letter or digit is left
    incident_check.py date [--value YYYY-MM-DD]
        the date, or standard input, when it is a real YYYY-MM-DD
    incident_check.py branch --date YYYY-MM-DD --slug SLUG
        `incident/<date>-<slug>`, when the slug is lowercase kebab-case
    incident_check.py reviews-dir --value VALUE
        `ok` when VALUE is a relative path inside the repository, as release_dir must be
    incident_check.py --self-test     runs every case below; exit 0 only if each one matches

A failed check prints `INVALID: <what>` to standard error and exits 1; exit 2 is usage.
Working days are Monday to Friday, counted as numpy.busday_count(incident + 1, start + 1)
counts them, with no holiday calendar: a holiday counts as a working day, so it can only
make a review late sooner, never excuse one.
"""
import argparse
import datetime
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "gates", "scripts"))
from project_rules import (FILE_NAME_MAX, PROJECT_KEYS, check_slug, cli_case,  # noqa: E402
                           error_message, error_of, parse_date, passed, report, result_of,
                           run_check, slug_of, text_input)

LATE_AFTER = 5


def working_days(incident, start):
    """Weekdays in (incident, start]."""
    first, last = parse_date(incident), parse_date(start)
    if last < first:
        raise ValueError(f"the review starts {start}, before the incident on {incident}")
    days = (last - first).days
    return sum(1 for offset in range(1, days + 1)
               if (first + datetime.timedelta(days=offset)).weekday() < 5)


def timeliness(incident, start):
    count = working_days(incident, start)
    return f"{count}\t{'late' if count > LATE_AFTER else 'on time'}"


# The longest name built from a slug is the branch's lock file, `<YYYY-MM-DD>-<slug>.lock`,
# longer than the review file, `<YYYY-MM-DD>-<slug>.md`.
SLUG_MAX = FILE_NAME_MAX - len("YYYY-MM-DD-") - len(".lock")


def branch(date, slug):
    parse_date(date)
    return f"incident/{date}-{check_slug('slug', slug)}"


WORKING_DAY_CASES = [
    ("Monday to the next Monday", "2026-10-12", "2026-10-19", "5\ton time"),
    ("Monday to the next Tuesday", "2026-10-12", "2026-10-20", "6\tlate"),
    ("Friday to the next Friday", "2026-10-16", "2026-10-23", "5\ton time"),
    ("a Saturday incident to Friday", "2026-10-17", "2026-10-23", "5\ton time"),
    ("a Saturday incident to the Monday after", "2026-10-17", "2026-10-26", "6\tlate"),
    ("the same day", "2026-10-16", "2026-10-16", "0\ton time"),
    ("a Monday incident to the Saturday after", "2026-10-12", "2026-10-17", "4\ton time"),
    ("a Sunday incident to the Monday a week on", "2026-10-18", "2026-10-26", "6\tlate"),
    ("over a year end", "2026-12-31", "2027-01-08", "6\tlate"),
    ("a leap day", "2028-02-28", "2028-03-06", "5\ton time"),
    ("a start before the incident", "2026-10-16", "2026-10-15", "ValueError"),
    ("a malformed date", "2026-10-1", "2026-10-16", "ValueError"),
    ("an impossible date", "2026-02-29", "2026-03-02", "ValueError"),
    ("a time after the date", "2026-10-16T09:00", "2026-10-16", "ValueError"),
]

BRANCH_CASES = [
    ("a kebab-case slug", "2026-10-16", "db-failover", "incident/2026-10-16-db-failover"),
    ("digits", "2026-10-16", "outage-2", "incident/2026-10-16-outage-2"),
    ("capitals", "2026-10-16", "DB-failover", "ValueError"),
    ("a space", "2026-10-16", "db failover", "ValueError"),
    ("a leading dash", "2026-10-16", "-db", "ValueError"),
    ("a double dash", "2026-10-16", "db--x", "ValueError"),
    ("a path", "2026-10-16", "../main", "ValueError"),
    ("dots", "2026-10-16", "db..x", "ValueError"),
    ("empty", "2026-10-16", "", "ValueError"),
    ("a trailing newline", "2026-10-16", "db\n", "ValueError"),
    ("a date with a trailing newline", "2026-10-16\n", "db", "ValueError"),
    ("a bad date", "2026-13-01", "db", "ValueError"),
]


def self_test():
    failures = 0
    for name, incident, start, expected in WORKING_DAY_CASES:
        failures += report("working-days", name, result_of(timeliness, incident, start), expected)
    for name, date, slug, expected in BRANCH_CASES:
        failures += report("branch", name, result_of(branch, date, slug), expected)
    # readiness_check.py's self-test covers the path rules; these pin the key and the unset.
    reviews_dir = PROJECT_KEYS["incident_reviews_dir"].check
    failures += report("reviews-dir", "a relative path", error_of(reviews_dir, "docs/incidents"),
                       "ok")
    named = error_message(lambda: reviews_dir("/tmp/incidents"))
    named = "ok" if named is None else named.split()[0]
    failures += report("reviews-dir", "the error names incident_reviews_dir", named,
                       "incident_reviews_dir")
    for value in ("None", "NONE", "none"):
        failures += report("reviews-dir", f"{value} is unset",
                           error_of(reviews_dir, value), "ValueError")
    script = os.path.abspath(__file__)
    for case in [
            ("late prints the count and late",
             ["working-days", "--incident", "2026-10-12", "--start", "2026-10-20"], "6\tlate", 0),
            ("a future incident is invalid",
             ["working-days", "--incident", "2026-10-20", "--start", "2026-10-12"], "INVALID:", 1),
            ("branch prints the branch", ["branch", "--date", "2026-10-16", "--slug", "db"],
             "incident/2026-10-16-db", 0),
            ("a bad slug is invalid", ["branch", "--date", "2026-10-16", "--slug", "A"],
             "INVALID:", 1),
            ("reviews-dir ok", ["reviews-dir", "--value", "docs/incidents"], "ok", 0),
            ("reviews-dir none", ["reviews-dir", "--value", "none"], "INVALID:", 1),
            ("no subcommand is usage", [], "", 2)]:
        failures += cli_case(script, *case)
    failures += cli_case(script, "slug prints the slug", ["slug", "--title", "DB failover!"],
                         "db-failover", 0, exact=True)
    failures += cli_case(script, "a slug is fitted to the branch's lock file",
                         ["slug", "--title", "e" * 300], "e" * 239, 0, exact=True)
    failures += cli_case(script, "date prints a real date", ["date"], "2026-10-12", 0,
                         input="2026-10-12\n")
    failures += cli_case(script, "a date holding shell text is refused before any use",
                         ["date"], "INVALID:", 1, input="2026-10-12$(touch x)\n")
    failures += cli_case(script, "slug reads the words from stdin", ["slug"], "rob-s-outage", 0,
                         input="Rob's outage\n")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    days = commands.add_parser("working-days")
    days.add_argument("--incident", required=True)
    days.add_argument("--start", required=True)
    commands.add_parser("slug").add_argument("--title")
    commands.add_parser("date").add_argument("--value")
    name = commands.add_parser("branch")
    name.add_argument("--date", required=True)
    name.add_argument("--slug", required=True)
    directory = commands.add_parser("reviews-dir")
    directory.add_argument("--value", required=True)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    checks = {"working-days": lambda: timeliness(args.incident, args.start),
              "slug": lambda: slug_of(text_input(args.title), SLUG_MAX),
              "date": lambda: parse_date(text_input(args.value)).isoformat(),
              "branch": lambda: branch(args.date, args.slug),
              "reviews-dir": passed(lambda: PROJECT_KEYS["incident_reviews_dir"].check(args.value))}
    return run_check(parser, checks, args.command)


if __name__ == "__main__":
    sys.exit(main())
