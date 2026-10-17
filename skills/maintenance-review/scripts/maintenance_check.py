#!/usr/bin/env python3
"""Maintenance-review checks, so the skill settles no age, share, or match by eye. Standard
library only.

Called by skills/maintenance-review/SKILL.md (Steps 1 to 3). The discipline keys are checked
by skills/release-readiness/scripts/readiness_check.py's `disciplines --gate maintenance`,
which holds every discipline's keys; this script checks the general ones. Every subcommand
reads its keys from project.json itself, so no value passes through shell text.

    maintenance_check.py config --config PATH
        one `<key>\t<value>` line per general maintenance key, the value as JSON — its
        default or "none" when unset — or INVALID for each key set in the wrong shape
    maintenance_check.py alerts --config PATH --today YYYY-MM-DD < PAGES
        one `<severity>\t<age>\t<package>\t<advisory>\t<manifest>\t<url>` line per open alert
        from Dependabot more than patch_sla_days old, Critical first, then oldest first, one
        per manifest as Dependabot raises them; PAGES is the output of
        `gh api --paginate --slurp`, a list of pages, each a list of alerts
    maintenance_check.py runbooks --config PATH --today YYYY-MM-DD
        one `<path>\t<last commit date, or uncommitted>` line per file under runbooks_dir
        whose last commit is more than 90 days old, or that no commit holds
    maintenance_check.py routes --config PATH < LINES
        each `<rule> <target>` line whose target is not exactly an on_call entry, as
        `<rule>\t<target>`, and each line that is not two fields, as `malformed\t<line>`
    maintenance_check.py share --config PATH --resolved N --preventive M
        `<share>%`, then `\tmeets <T>%` or `\tbelow <T>%` with debt_share_target set; with
        nothing resolved, `no issues resolved`
    maintenance_check.py drift --config PATH < OUTPUT
        `within <n>` or `over <n>`, against drift_threshold, for the one number printed
    maintenance_check.py --self-test     runs every case below; exit 0 only if each one matches

A failed check prints `INVALID: <what>` to standard error and exits 1; exit 2 is usage.
Ages are whole UTC calendar days. `created_at` is read as RFC 3339, moved to UTC, and cut to
its date; a commit's date is its committer date in UTC. An age equal to its limit is within
it, so an alert exactly N days old is not yet past its SLA. A share is shown rounded down to
one decimal, so a shown share never reads as meeting a target it misses.
"""
import argparse
import datetime
import json
import math
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "gates", "scripts"))
from project_rules import (check_command, check_repo_path, is_unset,  # noqa: E402
                           json_number, parse_date, positive_int, read_config, report,
                           result_of, single_number)

RUNBOOK_MAX_AGE = 90
DEFAULTS = {"on_call": "none", "iteration_days": 14, "debt_share_target": "none",
            "dependency_outdated_command": "none", "patch_sla_days": "none",
            "runbooks_dir": "none", "alert_routes_command": "none"}
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
# Read-only git, deaf to a global log.showSignature, which would print signature lines
# before the date, and reading each path literally, so a `*` in a runbook's name is no glob.
GIT = ["git", "-c", "log.showSignature=false", "--literal-pathspecs"]


def check_on_call(value):
    if not (isinstance(value, list) and value
            and all(isinstance(person, str) and person.split() == [person] for person in value)):
        raise ValueError("on_call is not a non-empty list of handles, one word each")


def check_target(key, value):
    json_number(key, value)
    if not 0 <= value <= 100:
        raise ValueError(f"{key} {value!r} is not a number from 0 to 100")


CHECKS = {"on_call": check_on_call,
          "iteration_days": lambda value: positive_int("iteration_days", value),
          "debt_share_target": lambda value: check_target("debt_share_target", value),
          "dependency_outdated_command": lambda value: check_command(
              "dependency_outdated_command", value),
          "patch_sla_days": lambda value: positive_int("patch_sla_days", value),
          "runbooks_dir": lambda value: check_repo_path("runbooks_dir", value),
          "alert_routes_command": lambda value: check_command("alert_routes_command", value)}


def resolve_config(config):
    """{key: value} for each general key, unset ones at their default; raise naming every
    key set in the wrong shape."""
    resolved, problems = {}, []
    for key, default in DEFAULTS.items():
        value = config.get(key)
        if is_unset(value):
            resolved[key] = default
            continue
        try:
            CHECKS[key](value)
        except ValueError as error:
            problems.append(str(error))
            continue
        resolved[key] = value
    if problems:
        raise ValueError("; ".join(problems))
    return resolved


def required(config, key):
    value = resolve_config(config)[key]
    if value == "none":
        raise ValueError(f"{key} is none, so this check has nothing to read")
    return value


def utc_date(timestamp):
    if not isinstance(timestamp, str) or not TIMESTAMP.fullmatch(timestamp):
        raise ValueError(f"created_at {timestamp!r} is not an RFC 3339 timestamp")
    moment = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return moment.astimezone(datetime.timezone.utc).date()


def stale_alerts(config, pages, today):
    """Rows for each open alert more than patch_sla_days old, Critical first, then oldest."""
    sla_days = required(config, "patch_sla_days")
    today = parse_date(today)
    if not (isinstance(pages, list) and all(isinstance(page, list) for page in pages)):
        raise ValueError("the alerts are not a list of pages, as `gh api --paginate --slurp` "
                         "prints them")
    rows = []
    for alert in (alert for page in pages for alert in page):
        try:
            if alert["state"] != "open":
                continue
            age = (today - utc_date(alert["created_at"])).days
            row = (alert["security_advisory"]["severity"], age,
                   alert["dependency"]["package"]["name"],
                   alert["security_advisory"]["ghsa_id"], alert["dependency"]["manifest_path"],
                   alert["html_url"])
        except (KeyError, TypeError):
            raise ValueError(f"alert {alert!r:.80} lacks a Dependabot alert field")
        if age > sla_days:
            rows.append(row)
    rows.sort(key=lambda row: (row[0] != "critical", -row[1]))
    return ["\t".join(str(cell) for cell in row) for row in rows]


def git_paths(*arguments):
    run = subprocess.run([*GIT, *arguments], capture_output=True, text=True, check=False,
                         env=dict(os.environ, TZ="UTC"))
    if run.returncode:
        raise ValueError(f"git {' '.join(arguments)} failed: {run.stderr.strip()}")
    return [line for line in run.stdout.split("\0" if "-z" in arguments else "\n") if line]


def stale_runbooks(config, today):
    """Each runbook on disk whose last commit is more than 90 days before today, or none."""
    directory = required(config, "runbooks_dir")
    today = parse_date(today)
    if not os.path.isdir(directory):
        raise ValueError(f"runbooks_dir {directory!r} is not a directory")
    if git_paths("rev-parse", "--is-shallow-repository") != ["false"]:
        raise ValueError("the checkout is shallow, so every file's last commit reads as the "
                         "clone's boundary; fetch the full history first")
    rows = [f"{path}\tuncommitted"
            for path in git_paths("ls-files", "-z", "--others", "--exclude-standard", "--",
                                  directory)]
    for path in git_paths("ls-files", "-z", "--", directory):
        if not os.path.exists(path):
            continue
        dates = git_paths("log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%d", "--",
                          path)
        if not dates:
            rows.append(f"{path}\tuncommitted")
        elif (today - parse_date(dates[0])).days > RUNBOOK_MAX_AGE:
            rows.append(f"{path}\t{dates[0]}")
    if not rows and not any(os.path.exists(path) for path in
                            git_paths("ls-files", "-z", "--", directory)):
        raise ValueError(f"runbooks_dir {directory!r} holds no runbook git can see — empty, "
                         "or gitignored")
    return sorted(rows)


def unrouted(config, lines):
    """Routes whose target is no on_call entry, compared exactly, and malformed lines."""
    people = resolve_config(config)["on_call"]
    people = [] if people == "none" else people
    rows = []
    for line in lines.splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 2:
            rows.append(f"malformed\t{line}")
        elif fields[1] not in people:
            rows.append(f"{fields[0]}\t{fields[1]}")
    return rows


def debt_share(config, resolved, preventive):
    target = resolve_config(config)["debt_share_target"]
    if resolved < 0 or preventive < 0 or preventive > resolved:
        raise ValueError(f"{preventive} preventive of {resolved} resolved is not a share")
    if resolved == 0:
        return "no issues resolved"
    share = 100 * preventive / resolved
    shown = f"{math.floor(share * 10) / 10:.1f}%"
    if target == "none":
        return shown
    return f"{shown}\t{'meets' if share >= target else 'below'} {target}%"


def drift(config, output):
    value = config.get("drift_threshold")
    if is_unset(value):
        raise ValueError("drift_threshold is none, so this check has nothing to compare")
    threshold = json_number("drift_threshold", value)
    value = single_number(output, "drift_check_command")
    return ("over" if float(value) > threshold else "within"), value


def alert(created_at, severity="high", state="open", name="left-pad"):
    return {"state": state, "created_at": created_at, "html_url": f"https://example.test/{name}",
            "dependency": {"package": {"name": name}, "manifest_path": "package-lock.json"},
            "security_advisory": {"severity": severity, "ghsa_id": "GHSA-xxxx-xxxx-xxxx"}}


def alert_names(pages, config=None, today="2026-10-17"):
    rows = result_of(stale_alerts, {"patch_sla_days": 30} if config is None else config, pages,
                     today)
    return rows if rows == "ValueError" else [row.split("\t")[2] for row in rows]


ALERT_CASES = [
    ("exactly at the SLA is within it", [[alert("2026-09-17T12:00:00Z")]], []),
    ("a day past the SLA", [[alert("2026-09-16T12:00:00Z")]], ["left-pad"]),
    ("a time behind UTC is read on its UTC date",
     [[alert("2026-09-16T20:00:00-08:00")]], []),
    ("a time ahead of UTC is read on its UTC date",
     [[alert("2026-09-17T02:00:00+05:00")]], ["left-pad"]),
    ("Critical before an older High",
     [[alert("2026-01-01T00:00:00Z", "high", name="old-high"),
       alert("2026-08-01T00:00:00Z", "critical", name="new-critical")]],
     ["new-critical", "old-high"]),
    ("oldest first within a severity",
     [[alert("2026-08-01T00:00:00Z", name="newer")],
      [alert("2026-01-01T00:00:00Z", name="older")]], ["older", "newer"]),
    ("a dismissed alert is not open", [[alert("2026-01-01T00:00:00Z", state="dismissed")]], []),
    ("no pages", [], []),
    ("one empty page", [[]], []),
    ("pages not slurped", [alert("2026-01-01T00:00:00Z")], "ValueError"),
    ("a date with no time", [[alert("2026-01-01")]], "ValueError"),
    ("a time with no zone", [[alert("2026-01-01T00:00:00")]], "ValueError"),
    ("a missing field", [[{"state": "open", "created_at": "2026-01-01T00:00:00Z"}]],
     "ValueError"),
]

ROUTE_CASES = [
    ("a route to a person", "db-down rob\n", ["rob"], []),
    ("a route to a channel", "db-down #ops\n", ["rob"], ["db-down\t#ops"]),
    ("a person matching only in case", "db-down Rob\n", ["rob"], ["db-down\tRob"]),
    ("a line with one field", "db-down\n", ["rob"], ["malformed\tdb-down"]),
    ("a line with three fields", "db-down rob ops\n", ["rob"], ["malformed\tdb-down rob ops"]),
    ("blank lines are skipped", "\n  \ndb-down rob\n", ["rob"], []),
    ("no rota routes nothing to a person", "db-down rob\n", "none", ["db-down\trob"]),
    ("a rota that is not a list", "db-down rob\n", "rob", "ValueError"),
]

SHARE_CASES = [
    ("a share meeting its target", (10, 2), 15, "20.0%\tmeets 15%"),
    ("a fractional target as configured", (10, 2), 12.3456789, "20.0%\tmeets 12.3456789%"),
    ("a share exactly at its target", (10, 2), 20, "20.0%\tmeets 20%"),
    ("a share below its target", (10, 1), 15, "10.0%\tbelow 15%"),
    ("a share just under its target never shows as it", (10000, 1996), 20, "19.9%\tbelow 20%"),
    ("no target", (3, 1), "none", "33.3%"),
    ("nothing resolved", (0, 0), 15, "no issues resolved"),
    ("more preventive than resolved", (2, 3), 15, "ValueError"),
    ("a negative count", (-1, 0), 15, "ValueError"),
    ("a target above 100", (10, 1), 120, "ValueError"),
    ("a negative target", (10, 1), -1, "ValueError"),
    ("a target as a string", (10, 1), "15", "ValueError"),
]

DRIFT_CASES = [
    ("below the threshold", "0.1\n", 0.25, ("within", "0.1")),
    ("equal to the threshold", "0.25\n", 0.25, ("within", "0.25")),
    ("above the threshold", "0.3\n", 0.25, ("over", "0.3")),
    ("an exponent-form threshold", "0.00002\n", 1e-5, ("over", "0.00002")),
    ("two numbers", "0.1\n0.2\n", 0.25, "ValueError"),
    ("a word around it", "psi=0.1\n", 0.25, "ValueError"),
    ("a threshold that is not a number", "0.1\n", "high", "ValueError"),
    ("a threshold of NaN", "0.1\n", float("nan"), "ValueError"),
    ("no threshold", "0.1\n", "none", "ValueError"),
    ("no output", "", 0.25, "ValueError"),
]

CONFIG_CASES = [
    ("nothing set takes every default", {}, dict(DEFAULTS)),
    ("none takes the default", {"iteration_days": "none"}, dict(DEFAULTS)),
    ("set keys resolve to themselves",
     {"on_call": ["rob", "ana"], "iteration_days": 7, "debt_share_target": 15,
      "patch_sla_days": 30, "runbooks_dir": "docs/runbooks"},
     dict(DEFAULTS, on_call=["rob", "ana"], iteration_days=7, debt_share_target=15,
          patch_sla_days=30, runbooks_dir="docs/runbooks")),
    ("an iteration of zero days", {"iteration_days": 0}, "ValueError"),
    ("an iteration as a string", {"iteration_days": "14"}, "ValueError"),
    ("an SLA of minus one", {"patch_sla_days": -1}, "ValueError"),
    ("a target above 100", {"debt_share_target": 101}, "ValueError"),
    ("a target of NaN", {"debt_share_target": float("nan")}, "ValueError"),
    ("a rota as a string", {"on_call": "rob"}, "ValueError"),
    ("an empty rota", {"on_call": []}, "ValueError"),
    ("a rota entry with a space", {"on_call": ["rob kruy"]}, "ValueError"),
    ("a rota entry with a tab", {"on_call": ["rob\tkruy"]}, "ValueError"),
    ("runbooks outside the repository", {"runbooks_dir": "/srv/runbooks"}, "ValueError"),
    ("a command that is not a string", {"alert_routes_command": ["routes"]}, "ValueError"),
]


def runbook_cases():
    """A throwaway repository, deaf to the user's git configuration as sarif_gate.py's
    fixtures are, holding runbooks at 90 and 91 days, one 91 days old in UTC but 90 in the
    fixture's Tokyo time, one untracked, one staged, one deleted."""
    failures = 0
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                       GIT_COMMITTER_EMAIL="t@t", TZ="Asia/Tokyo")
    with tempfile.TemporaryDirectory() as root:
        def git(*arguments, date=None):
            dated = dict(environment, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date) \
                if date else environment
            subprocess.run(["git", "-C", root, "-c", "core.hooksPath=/dev/null", *arguments],
                           env=dated, capture_output=True, check=True)

        def write(name):
            with open(os.path.join(root, "runbooks", name), "w", encoding="utf-8") as handle:
                handle.write(name)

        os.makedirs(os.path.join(root, "runbooks"))
        git("init", "-q", "--template=")
        for name, date in (("ninety.md", "2026-07-19T23:00:00Z"),
                           ("ninety-one.md", "2026-07-18T12:00:00Z"),
                           ("utc-ninety-one.md", "2026-07-18T20:00:00Z"),
                           ("deleted.md", "2026-01-01T12:00:00Z")):
            write(name)
            git("add", "--", f"runbooks/{name}")
            git("commit", "-q", "-m", name, date=date)
        os.remove(os.path.join(root, "runbooks", "deleted.md"))
        write("draft.md")
        write("staged.md")
        git("add", "--", "runbooks/staged.md")
        here, inherited = os.getcwd(), dict(os.environ)
        os.chdir(root)
        os.environ.clear()
        os.environ.update(environment)
        try:
            failures += report("runbooks", "91 days and uncommitted are listed; 90 and deleted "
                               "are not",
                               result_of(stale_runbooks, {"runbooks_dir": "runbooks"},
                                         "2026-10-17"),
                               ["runbooks/draft.md\tuncommitted",
                                "runbooks/ninety-one.md\t2026-07-18",
                                "runbooks/staged.md\tuncommitted",
                                "runbooks/utc-ninety-one.md\t2026-07-18"])
            failures += report("runbooks", "a missing directory",
                               result_of(stale_runbooks, {"runbooks_dir": "playbooks"},
                                         "2026-10-17"), "ValueError")
            os.makedirs(os.path.join(root, "empty"))
            failures += report("runbooks", "an empty directory is no list of runbooks",
                               result_of(stale_runbooks, {"runbooks_dir": "empty"},
                                         "2026-10-17"), "ValueError")
            failures += report("runbooks", "runbooks_dir none",
                               result_of(stale_runbooks, {}, "2026-10-17"), "ValueError")
            for name, date in (("a*.md", "2026-01-01T12:00:00Z"),
                               ("ab.md", "2026-10-01T12:00:00Z")):
                write(name)
                git("--literal-pathspecs", "add", "--", f"runbooks/{name}")
                git("commit", "-q", "-m", name, date=date)
            rows = result_of(stale_runbooks, {"runbooks_dir": "runbooks"}, "2026-10-17")
            failures += report("runbooks", "a runbook named with a * is read literally",
                               [row for row in rows if row.startswith("runbooks/a")],
                               ["runbooks/a*.md\t2026-01-01"])
            shallow = os.path.join(root, "shallow")
            subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{root}", shallow],
                           env=environment, capture_output=True, check=True)
            os.chdir(shallow)
            failures += report("runbooks", "a shallow clone is refused",
                               result_of(stale_runbooks, {"runbooks_dir": "runbooks"},
                                         "2026-10-17"), "ValueError")
        finally:
            os.chdir(here)
            os.environ.clear()
            os.environ.update(inherited)
    return failures


def cli_cases():
    failures = 0
    script = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as directory:
        config = os.path.join(directory, "project.json")
        with open(config, "w", encoding="utf-8") as handle:
            json.dump({"patch_sla_days": 30, "on_call": ["rob"], "debt_share_target": 20,
                       "drift_threshold": 0.25, "alert_routes_command": "routes\tall"}, handle)
        pages = json.dumps([[alert("2026-01-01T00:00:00Z")]])
        for name, arguments, stdin, expected_output, expected_exit in [
                ("config prints JSON values", ["config"], "",
                 'on_call\t["rob"]', 0),
                ("alerts prints the row", ["alerts", "--today", "2026-10-17"], pages,
                 "high\t289\tleft-pad", 0),
                ("alerts rejects text that is not JSON", ["alerts", "--today", "2026-10-17"],
                 "<html>", "INVALID:", 1),
                ("drift over", ["drift"], "0.3\n", "over 0.3", 0),
                ("drift within", ["drift"], "0.1\n", "within 0.1", 0),
                ("routes prints unrouted", ["routes"], "a #ops\n", "a\t#ops", 0),
                ("share with a target", ["share", "--resolved", "4", "--preventive", "1"], "",
                 "25.0%\tmeets 20%", 0)]:
            run = subprocess.run([sys.executable, script, *arguments, "--config", config],
                                 input=stdin, capture_output=True, text=True, check=False)
            stream = run.stderr if expected_output.startswith("INVALID") else run.stdout
            shown = stream.strip()[:len(expected_output)]
            failures += report("cli", name, (shown, run.returncode),
                               (expected_output, expected_exit))
        run = subprocess.run([sys.executable, script, "config", "--config", config],
                             capture_output=True, text=True, check=False)
        failures += report("cli", "a command with a tab stays on one line",
                           [line for line in run.stdout.splitlines()
                            if line.startswith("alert_routes_command")],
                           ['alert_routes_command\t"routes\\tall"'])
    run = subprocess.run([sys.executable, script], capture_output=True, text=True, check=False)
    failures += report("cli", "no subcommand is usage", run.returncode, 2)
    return failures


def self_test():
    failures = 0
    for name, pages, expected in ALERT_CASES:
        failures += report("alerts", name, alert_names(pages), expected)
    failures += report("alerts", "patch_sla_days none", alert_names([[]], {}), "ValueError")
    for name, lines, on_call, expected in ROUTE_CASES:
        failures += report("routes", name, result_of(unrouted, {"on_call": on_call}, lines),
                           expected)
    for name, counts, target, expected in SHARE_CASES:
        failures += report("share", name,
                           result_of(debt_share, {"debt_share_target": target}, *counts),
                           expected)
    for name, output, threshold, expected in DRIFT_CASES:
        failures += report("drift", name,
                           result_of(drift, {"drift_threshold": threshold}, output), expected)
    for name, config, expected in CONFIG_CASES:
        failures += report("config", name, result_of(resolve_config, config), expected)
    failures += runbook_cases()
    failures += cli_cases()
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    subcommands = {name: commands.add_parser(name)
                   for name in ("config", "alerts", "runbooks", "routes", "share", "drift")}
    for subcommand in subcommands.values():
        subcommand.add_argument("--config", required=True)
    for name in ("alerts", "runbooks"):
        subcommands[name].add_argument("--today", required=True)
    subcommands["share"].add_argument("--resolved", type=int, required=True)
    subcommands["share"].add_argument("--preventive", type=int, required=True)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.command not in subcommands:
        parser.print_usage(sys.stderr)
        return 2
    try:
        config = read_config(args.config)
        if args.command == "config":
            rows = [f"{key}\t{json.dumps(value)}" for key, value in resolve_config(config).items()]
        elif args.command == "alerts":
            try:
                pages = json.loads(sys.stdin.read())
            except ValueError as error:
                raise ValueError(f"the alerts are not JSON: {error}")
            rows = stale_alerts(config, pages, args.today)
        elif args.command == "runbooks":
            rows = stale_runbooks(config, args.today)
        elif args.command == "routes":
            rows = unrouted(config, sys.stdin.read())
        elif args.command == "share":
            rows = [debt_share(config, args.resolved, args.preventive)]
        else:
            rows = [" ".join(drift(config, sys.stdin.read()))]
    except ValueError as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1
    for row in rows:
        print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
