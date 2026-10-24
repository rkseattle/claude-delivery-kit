#!/usr/bin/env python3
"""Retirement-record checks, so the skill commits no record by eye. Standard library only, but
for the CommonMark parser project_rules.fence_split loads.

Called by skills/retire-system/SKILL.md (Steps 1, 4 and 5).

    retire_check.py retirements-dir --config PATH
        `ok` when retirements_dir is a relative path inside the repository, as release_dir
        must be
    retire_check.py name --value NAME
        `retire/<name>`, when the name is lowercase kebab-case
    retire_check.py record --file PATH --config PATH --today YYYY-MM-DD
        `done` when the record holds exactly the sections User notice, Data, Infrastructure,
        and Credentials, in that order, each `Status: done` with every checklist item ticked
        and one `Confirmed:` line naming the service owner, and no `<placeholder>` left in its
        items or notice; otherwise `pending: <section>, ...`
        naming each section still `Status: pending`
    retire_check.py --self-test     runs every case below; exit 0 only if each one matches

A failed check prints `INVALID: <what>` to standard error and exits 1; exit 2 is usage.

The service owner is `roles.service_owner`, or with none there, git's `user.name`, as the
skill writes it; the record's `Service owner:` line and every confirmation must name exactly
that person, and a confirmation is dated from the record's `Started:` date to today.

The record is read by allowlist, not by searching for what might be wrong: outside a fenced
code block, such as the drafted user notice, every line must be one the template writes — a
`# Retirement — ` title, a `Service owner:` or `Started:` line, a `## ` section heading, a
`Status:` or `Confirmed:` line, a `- [ ] <item>` or `- [x] <item>` line, or a blank. Any
other line is INVALID, so no other list, quote, or comment form can hold an unticked item a
reader would see. Fences are split by project_rules.fence_split, as readiness_check.py
splits them.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "gates", "scripts"))
from project_rules import (check_repo_path, check_slug, cli_case, error_of,  # noqa: E402
                           fence_split, isolated_git_environment, process_state,
                           is_unset, parse_date, read_config, report, result_of, run_check)

SECTIONS = ("User notice", "Data", "Infrastructure", "Credentials")
STATUS = re.compile(r"^Status: (pending|done)$")
ITEM = re.compile(r"^- \[([ x])\] \S.*$")
CONFIRMED = re.compile(r"^Confirmed: (\S.*?) (\d{4}-\d{2}-\d{2})(?:, relayed by \S.*)?$")
STARTED = re.compile(r"^Started: (\d{4}-\d{2}-\d{2})$")
OWNER = re.compile(r"^Service owner: (\S.*)$")
# Exactly what the skill's template leaves for an answer, so an email address or URL in angle
# brackets in the sent notice is never taken for one.
TEMPLATE_PLACEHOLDERS = ("<each user group>", "<data store>", "<resource>", "<credential name>",
                         "<path>", "<line>", "<where>", "<to confirm>", "<the drafted notice",
                         "<name>", " or archived at ")
TITLE = re.compile(r"^# Retirement — (\S.*)$")
HEADER_LINES = (TITLE, OWNER, STARTED)  # each exactly once
SECTION_LINES = (STATUS, CONFIRMED, ITEM)


def branch(name):
    return f"retire/{check_slug('name', name)}"


def service_owner(config):
    roles = config.get("roles") or {}
    if not isinstance(roles, dict):
        raise ValueError("roles is not a map from each role to its person")
    owner = roles.get("service_owner")
    if not is_unset(owner):
        if not isinstance(owner, str):
            raise ValueError("roles.service_owner is not a name")
        return owner.strip()
    run = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True,
                         check=False)
    if run.returncode or not run.stdout.strip():
        raise ValueError("no roles.service_owner and no git user.name to name the owner by")
    return run.stdout.strip()


def structure(text):
    """(header lines, [(heading, [lines], [fenced lines])]): the lines outside fences each
    checked against the allowlist its place in the record has, and a section's fenced lines,
    such as the drafted notice, kept apart."""
    rows, unclosed = fence_split(text)
    if unclosed:
        raise ValueError("a code fence in the record never closes")
    header, sections = [], []
    for line, fenced in rows:
        line = line.rstrip()
        if fenced:
            if sections:
                sections[-1][2].append(line)
            continue
        if not line:
            continue
        if line.startswith("## "):
            sections.append((line[3:].strip(), [], []))
            continue
        allowed = SECTION_LINES if sections else HEADER_LINES
        if not any(pattern.match(line) for pattern in allowed):
            hint = " (a ticked item is `[x]`, lowercase)" if "[X]" in line else ""
            raise ValueError(f"the record holds {line!r}, which its template never "
                             f"writes{hint}")
        (sections[-1][1] if sections else header).append(line)
    return header, sections


def one(pattern, lines, what):
    matches = [match for match in map(pattern.match, lines) if match]
    if len(matches) != 1:
        raise ValueError(f"the record has {len(matches)} {what} lines, not one")
    return matches[0]


def section_state(heading, lines, fenced, owner, started, today):
    status = one(STATUS, lines, f"{heading} status").group(1)
    items = [ITEM.match(line).group(1) for line in lines if ITEM.match(line)]
    if not items:
        raise ValueError(f"{heading} has no checklist item")
    confirmations = [CONFIRMED.match(line) for line in lines if CONFIRMED.match(line)]
    if status == "pending":
        if confirmations:
            raise ValueError(f"{heading} is pending but records a confirmation")
        return "pending"
    if " " in items:
        raise ValueError(f"{heading} is done with an unticked item")
    left = [line for line in lines + fenced
            if any(placeholder in line for placeholder in TEMPLATE_PLACEHOLDERS)]
    if left:
        raise ValueError(f"{heading} is done but still holds {left[0]!r}, template text the "
                         "service owner's answer replaces — for a Data item, name only the one "
                         "of `migrated to` or `archived at` that happened")
    if len(confirmations) != 1:
        raise ValueError(f"{heading} is done without one `Confirmed: <name> <YYYY-MM-DD>` line")
    name, date = confirmations[0].groups()
    if name != owner:
        raise ValueError(f"{heading} is confirmed by {name!r}, not the service owner {owner!r}")
    if not started <= parse_date(date) <= today:
        raise ValueError(f"{heading} is confirmed on {date}, outside {started} to {today}")
    return "done"


def record_state(text, owner, today, name=None):
    today = parse_date(today)
    header, sections = structure(text)
    headings = tuple(heading for heading, _, _ in sections)
    if headings != SECTIONS:
        raise ValueError(f"the sections are {', '.join(headings) or 'none'}, not "
                         + ", ".join(SECTIONS))
    title = one(TITLE, header, "`# Retirement — ` title")
    if any(placeholder in title.group(0) for placeholder in TEMPLATE_PLACEHOLDERS):
        raise ValueError(f"the title {title.group(0)!r} still holds a template placeholder")
    if name is not None and title.group(1) != name:
        raise ValueError(f"the title names {title.group(1)!r}, but the record is {name}.md")
    named = one(OWNER, header, "Service owner").group(1)
    if named != owner:
        raise ValueError(f"the record names {named!r} as service owner, not {owner!r}")
    started = parse_date(one(STARTED, header, "Started").group(1))
    pending = [heading for heading, lines, fenced in sections
               if section_state(heading, lines, fenced, owner, started, today) == "pending"]
    return f"pending: {', '.join(pending)}" if pending else "done"


def check_dir(config):
    check_repo_path("retirements_dir", config.get("retirements_dir"))
    return "ok"


def record(states, owner="rob"):
    """A record whose sections take the given (status, items, confirmation) states."""
    parts = [f"# Retirement — billing\n\nService owner: {owner}\nStarted: 2026-10-17\n"]
    for heading, (status, items, confirmed) in zip(SECTIONS, states):
        parts.append(f"## {heading}\n\nStatus: {status}\n")
        parts.extend(f"- [{tick}] item\n" for tick in items)
        if confirmed:
            parts.append(f"{confirmed}\n")
    return "\n".join(parts)


DONE = ("done", "x", "Confirmed: rob 2026-10-18")
PENDING = ("pending", " ", None)


def with_first(state):
    return record([state] + [DONE] * 3)


def first_section_with(line):
    return record([DONE] * 4).replace("- [x] item\n", f"- [x] item\n{line}\n", 1)


RECORD_CASES = [
    ("every section done", record([DONE] * 4), "done"),
    ("one section pending", record([DONE, PENDING, DONE, DONE]), "pending: Data"),
    ("a relayed confirmation", with_first(("done", "x", "Confirmed: rob 2026-10-18, relayed "
                                                        "by ana")), "done"),
    ("a fresh record", record([PENDING] * 4),
     "pending: User notice, Data, Infrastructure, Credentials"),
    ("a section missing", record([DONE] * 3), "ValueError"),
    ("sections out of order", record([DONE] * 4).replace("## Data", "## Tmp")
     .replace("## Infrastructure", "## Data").replace("## Tmp", "## Infrastructure"),
     "ValueError"),
    ("a heading spelled Infra", record([DONE] * 4).replace("## Infrastructure", "## Infra"),
     "ValueError"),
    ("an extra section", record([DONE] * 4) + "\n## Notes\n", "ValueError"),
    ("two status lines", record([DONE] * 4).replace("Status: done\n",
                                                    "Status: done\nStatus: done\n", 1),
     "ValueError"),
    ("a status of complete", with_first(("complete", "x", "Confirmed: rob 2026-10-18")),
     "ValueError"),
    ("an empty checklist", with_first(("pending", "", None)), "ValueError"),
    ("done with an unticked item", with_first(("done", "x ", "Confirmed: rob 2026-10-18")),
     "ValueError"),
    ("done with a nested unticked item", first_section_with("  - [ ] sub-item"), "ValueError"),
    ("done with a starred unticked item", first_section_with("* [ ] revoke key"), "ValueError"),
    ("done with an empty unticked item", first_section_with("- [ ]"), "ValueError"),
    ("done with no confirmation", with_first(("done", "x", None)), "ValueError"),
    ("a confirmation with no date", with_first(("done", "x", "Confirmed: rob")), "ValueError"),
    ("an impossible confirmation date", with_first(("done", "x", "Confirmed: rob 2026-02-30")),
     "ValueError"),
    ("a confirmation after today", with_first(("done", "x", "Confirmed: rob 2026-10-20")),
     "ValueError"),
    ("a confirmation before the start", with_first(("done", "x", "Confirmed: rob 2026-10-16")),
     "ValueError"),
    ("a confirmation by someone else", with_first(("done", "x", "Confirmed: mallory "
                                                                "2026-10-18")), "ValueError"),
    ("a record naming someone else as owner", record([DONE] * 4, owner="mallory"),
     "ValueError"),
    ("two confirmations", with_first(("done", "x", "Confirmed: rob 2026-10-18\n"
                                                   "Confirmed: rob 2026-10-18")), "ValueError"),
    ("pending with a confirmation", with_first(("pending", " ", "Confirmed: rob 2026-10-18")),
     "ValueError"),
    ("an indented confirmation is no template line",
     with_first(("pending", " ", "  Confirmed: rob 2026-10-18")), "ValueError"),
    ("trailing spaces on template lines", record([DONE] * 4).replace("Service owner: rob",
                                                                    "Service owner: rob  ")
     .replace("Status: done", "Status: done "), "done"),
    ("no title", record([DONE] * 4).replace("# Retirement — billing\n", ""), "ValueError"),
    ("two titles", "# Retirement — x\n" + record([DONE] * 4), "ValueError"),
    ("a done item still holding a placeholder",
     first_section_with("- [x] billing-db — infra/db.tf:4 — migrated to <where>"), "ValueError"),
    ("a done notice still holding a placeholder",
     first_section_with("```\nThe service retires on <to confirm>.\n```"), "ValueError"),
    ("an email address and a URL in a done notice",
     first_section_with("```\nQuestions: Rob K <rob@example.com>, see "
                        "<https://status.example.com>.\n```"), "done"),
    ("angle brackets that are no placeholder", first_section_with(
        "- [x] archived at s3://archive/<bucket>/2026, where a < b > c"), "done"),
    *[(f"a done item holding {token.strip()!r}",
       first_section_with(f"- [x] x {token} y"), "ValueError")
      for token in ("<each user group>", "<data store>", "<resource>", "<path>", "<line>",
                    "<the drafted notice, in a fenced block>", " or archived at ")],
    ("a title still holding <name>",
     record([DONE] * 4).replace("# Retirement — billing", "# Retirement — <name>"), "ValueError"),
    ("a placeholder in a later section", record([DONE] * 4).replace(
        "## Credentials\n\nStatus: done\n\n- [x] item",
        "## Credentials\n\nStatus: done\n\n- [x] <credential name> — revoked"), "ValueError"),
    ("a pending notice may hold placeholders",
     record([("pending", " ", None)] + [DONE] * 3).replace(
         "- [ ] item\n", "- [ ] item\n```\nRetires on <to confirm>.\n```\n", 1),
     "pending: User notice"),
    ("a pending section may hold placeholders",
     record([("pending", " ", None)] + [DONE] * 3).replace("- [ ] item", "- [ ] <where>", 1),
     "pending: User notice"),
    ("a closed fence in a blockquote is code, closed",
     first_section_with("> ```\n> - [ ] x\n> ```"), "done"),
    ("a closed fence in a nested list item",
     first_section_with("  - b\n    ```\n    - [ ] x\n    ```"), "ValueError"),
    ("a status inside the drafted notice is not read",
     first_section_with("```\nStatus: pending\n## Data\n```"), "done"),
    ("a tilde line inside a backtick fence does not close it",
     first_section_with("```\n~~~\n## Data\n```"), "done"),
    ("a fence that never closes", first_section_with("```\n## Notes"), "ValueError"),
    ("a fence left open at a record's end with no final newline",
     record([DONE] * 4).rstrip("\n") + "\n```\n- [ ] hidden", "ValueError"),
    ("a marker indented four spaces is no fence",
     first_section_with("\n    ```\n\n- [ ] revoke key\n\n    ```"), "ValueError"),
    ("a backtick in the opener's info string is no fence",
     first_section_with("\n```x`y\n- [ ] revoke key\n```"), "ValueError"),
    ("a closer with an info string closes nothing",
     first_section_with("\n```\n```x\n```\n- [ ] revoke key\n```"), "ValueError"),
    ("an ordered unticked item", first_section_with("1. [ ] revoke key"), "ValueError"),
    ("a parenthesized ordered unticked item", first_section_with("1) [ ] revoke key"),
     "ValueError"),
    ("a quoted unticked item", first_section_with("> - [ ] quoted"), "ValueError"),
    ("an item inside an HTML comment", first_section_with("<!--\n- [ ] hidden\n-->"),
     "ValueError"),
    ("a capital X", first_section_with("- [X] item"), "ValueError"),
    ("a line of prose", first_section_with("Revoked the key by hand."), "ValueError"),
    ("a prose line in the header", record([DONE] * 4).replace("Started:", "Note: x\nStarted:"),
     "ValueError"),
]

NAME_CASES = [
    ("a kebab-case name", "billing-api", "retire/billing-api"),
    ("digits", "api-v2", "retire/api-v2"),
    ("capitals", "Billing", "ValueError"),
    ("a path", "../main", "ValueError"),
    ("a space", "billing api", "ValueError"),
    ("a trailing newline", "billing\n", "ValueError"),
    ("empty", "", "ValueError"),
]


def owner_fallback_cases():
    """git's user.name stands in for an absent role, read from a throwaway global config as
    sarif_gate.py's fixtures isolate git; with neither, the check refuses."""
    failures = 0
    with tempfile.TemporaryDirectory() as directory:
        named = os.path.join(directory, "named.gitconfig")
        with open(named, "w", encoding="utf-8") as handle:
            handle.write("[user]\n\tname = Rob K\n")
        for name, config, config_file, expected in [
                ("no role reads git's user.name", {}, named, "Rob K"),
                ("a blank role reads git's user.name",
                 {"roles": {"service_owner": "  "}}, named, "Rob K"),
                ("no role and no git name", {}, os.devnull, "ValueError")]:
            with process_state(isolated_git_environment(GIT_CONFIG_GLOBAL=config_file),
                               directory):
                failures += report("owner", name, result_of(service_owner, config), expected)
    return failures


def self_test():
    failures = 0
    for name, text, expected in RECORD_CASES:
        failures += report("record", name, result_of(record_state, text, "rob", "2026-10-19"),
                           expected)
    failures += report("record", "a title naming another record's file",
                       result_of(record_state, record([DONE] * 4), "rob", "2026-10-19",
                                 "payments"), "ValueError")
    failures += report("record", "a title naming its own file",
                       result_of(record_state, record([DONE] * 4), "rob", "2026-10-19",
                                 "billing"), "done")
    for name, value, expected in NAME_CASES:
        failures += report("name", name, result_of(branch, value), expected)
    for name, value, expected in [("a relative path", "docs/retirements", "ok"),
                                  ("absent", None, "ValueError"),
                                  ("none", "none", "ValueError"),
                                  ("outside the repository", "../retirements", "ValueError")]:
        failures += report("retirements-dir", name,
                           error_of(check_dir, {"retirements_dir": value}), expected)
    failures += report("owner", "the configured service owner, stripped",
                       result_of(service_owner, {"roles": {"service_owner": "ana "}}), "ana")
    failures += report("owner", "roles as a list",
                       result_of(service_owner, {"roles": ["ana"]}), "ValueError")
    failures += report("owner", "a service owner that is not a name",
                       result_of(service_owner, {"roles": {"service_owner": ["ana"]}}),
                       "ValueError")
    failures += owner_fallback_cases()
    script = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as directory:
        done = os.path.join(directory, "billing.md")
        with open(done, "w", encoding="utf-8") as handle:
            handle.write(record([DONE] * 4))
        config = os.path.join(directory, "project.json")
        with open(config, "w", encoding="utf-8") as handle:
            handle.write('{"retirements_dir": "docs/retirements", '
                         '"roles": {"service_owner": "rob"}}')
        record_arguments = ["--config", config, "--today", "2026-10-19"]
        for case in [
                ("record done", ["record", "--file", done, *record_arguments], "done", 0),
                ("a missing record", ["record", "--file", os.path.join(directory, "x.md"),
                                      *record_arguments], "INVALID:", 1),
                ("name prints the branch", ["name", "--value", "billing"], "retire/billing", 0),
                ("a bad name", ["name", "--value", "B"], "INVALID:", 1),
                ("retirements-dir ok", ["retirements-dir", "--config", config], "ok", 0),
                ("no subcommand is usage", [], "", 2)]:
            failures += cli_case(script, *case)
    return 1 if failures else 0


def read_record(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as error:
        raise ValueError(f"the record is unreadable: {error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("retirements-dir").add_argument("--config", required=True)
    commands.add_parser("name").add_argument("--value", required=True)
    checked = commands.add_parser("record")
    for option in ("--file", "--config", "--today"):
        checked.add_argument(option, required=True)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    checks = {"retirements-dir": lambda: check_dir(read_config(args.config)),
              "name": lambda: branch(args.value),
              "record": lambda: record_state(read_record(args.file),
                                             service_owner(read_config(args.config)),
                                             args.today,
                                             os.path.splitext(os.path.basename(args.file))[0])}
    return run_check(parser, checks, args.command)


if __name__ == "__main__":
    sys.exit(main())
