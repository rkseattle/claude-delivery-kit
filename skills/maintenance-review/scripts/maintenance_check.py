#!/usr/bin/env python3
"""Maintenance-review checks, so the skill settles no age, share, or match by eye. Standard
library only, but for the PyYAML vendored in gates/scripts/_vendor that alert-rules loads.

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
    maintenance_check.py alert-rules --config PATH
        one `<file>\t<alert>\t<lacks>` line per Prometheus alerting rule under alert_rules_dir
        naming no SLO, no runbook, or neither — `no SLO`, `no runbook`, or both, joined by
        `, ` — the two halves of Appendix B5's rule
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
from project_rules import (MARKDOWN_VENDOR, YAML_VENDOR, check_command,  # noqa: E402
                           check_repo_path, cli_case, collected_errors, foreign_code, is_unset,
                           isolated_git_environment, json_number, parse_date, positive_int,
                           process_state, read_config, report, result_of, run_git, single_number,
                           vendored)

RUNBOOK_MAX_AGE = 90
DEFAULTS = {"on_call": "none", "iteration_days": 14, "debt_share_target": "none",
            "dependency_outdated_command": "none", "patch_sla_days": "none",
            "runbooks_dir": "none", "alert_routes_command": "none"}
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
# Read-only git, deaf to a global log.showSignature, which would print signature lines
# before the date, and reading each path literally, so a `*` in a runbook's name is no glob.
GIT_OPTIONS = ["-c", "log.showSignature=false", "--literal-pathspecs"]


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
    problems = collected_errors(lambda key=key: CHECKS[key](config.get(key))
                                for key in DEFAULTS if not is_unset(config.get(key)))
    if problems:
        raise ValueError("; ".join(problems))
    return {key: default if is_unset(config.get(key)) else config.get(key)
            for key, default in DEFAULTS.items()}


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
    output = run_git(None, *GIT_OPTIONS, *arguments, environment=dict(os.environ, TZ="UTC"))
    return [line for line in output.split("\0" if "-z" in arguments else "\n") if line]


def last_commit_dates(directory):
    """{path: the UTC date of the newest commit touching it} under directory, from one
    `git log` pass, newest first, so a path's first appearance is its last commit. Paths are
    relative to the current directory, as `git ls-files` prints them, and NUL-separated, so
    a project root below the repository's top level, or a quote in a name, still matches."""
    dates, current = {}, None
    for token in git_paths("log", "-z", "--relative", "--format=\x01%cd",
                           "--date=format-local:%Y-%m-%d", "--name-only", "--", directory):
        token = token.lstrip("\n")
        if token.startswith("\x01"):
            current = token[1:]
        elif token and current:
            dates.setdefault(token, current)
    return dates


def stale_runbooks(config, today):
    """Each runbook on disk whose last commit is more than 90 days before today, or none."""
    directory = existing_dir("runbooks_dir", required(config, "runbooks_dir"))
    today = parse_date(today)
    if git_paths("rev-parse", "--is-shallow-repository") != ["false"]:
        raise ValueError("the checkout is shallow, so every file's last commit reads as the "
                         "clone's boundary; fetch the full history first")
    rows = [f"{path}\tuncommitted"
            for path in git_paths("ls-files", "-z", "--others", "--exclude-standard", "--",
                                  directory)]
    tracked = [path for path in git_paths("ls-files", "-z", "--", directory)
               if os.path.exists(path)]
    last = last_commit_dates(directory)
    for path in tracked:
        if path not in last:
            rows.append(f"{path}\tuncommitted")
        elif (today - parse_date(last[path])).days > RUNBOOK_MAX_AGE:
            rows.append(f"{path}\t{last[path]}")
    if not rows and not tracked:
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


RUNBOOK_KEYS = ("runbook_url", "runbook")
SLO_KEYS = ("slo", "sloth_slo")


def existing_dir(key, value):
    if not os.path.isdir(value):
        raise ValueError(f"{key} {value!r} is not a directory")
    return value


# The fields Prometheus's rule-file parser (rulefmt) accepts; it rejects any other.
GROUP_KEYS = {"name", "interval", "limit", "query_offset", "labels", "rules"}
# prometheus-operator's PrometheusRule adds one group field for Thanos Ruler.
OPERATOR_GROUP_KEYS = GROUP_KEYS | {"partial_response_strategy"}
RULE_KEYS = {"alert", "record", "expr", "for", "keep_firing_for", "labels", "annotations"}


def rule_groups(document, path):
    """The rule groups of a Prometheus rule file or a prometheus-operator PrometheusRule,
    held to rulefmt's fields; [] for another Kubernetes manifest, such as a kustomization,
    or a Sloth SLO spec beside the rules it generates."""
    allowed = GROUP_KEYS
    if isinstance(document, dict) and "kind" in document:
        if document["kind"] != "PrometheusRule":
            return []
        document, allowed = document.get("spec"), OPERATOR_GROUP_KEYS
    if isinstance(document, dict) and "slos" in document and "groups" not in document:
        return []
    groups = document.get("groups", False) if isinstance(document, dict) else False
    groups = [] if groups is None else groups
    if not isinstance(groups, list):
        raise ValueError(f"{path} is not Prometheus rule groups")
    for group in groups:
        if not (isinstance(group, dict) and group.get("name")):
            raise ValueError(f"{path} holds a rule group that is not a named map")
        unknown = set(group) - allowed
        if unknown or not isinstance(group.get("rules") or [], list):
            raise ValueError(f"{path}'s group {group['name']} has "
                             + (f"fields {sorted(unknown)} rulefmt rejects" if unknown
                                else "rules that are not a list"))
        for rule in group.get("rules") or []:
            if not isinstance(rule, dict) or len({"alert", "record"} & set(rule)) != 1 \
                    or set(rule) - RULE_KEYS or not rule.get("expr"):
                raise ValueError(f"{path}'s group {group['name']} holds {rule!r:.60}, not one "
                                 "alerting or recording rule of rulefmt's fields")
    return groups


def unlinked_alerts(config):
    """Each alerting rule naming no SLO or no runbook, by file and alert, with what it lacks."""
    check_repo_path("alert_rules_dir", config.get("alert_rules_dir"))
    directory = existing_dir("alert_rules_dir", config["alert_rules_dir"])
    vendored(YAML_VENDOR)
    import yaml
    def unreadable(error):
        raise ValueError(f"{error.filename} is unreadable, so its rules went unchecked: "
                         f"{error.strerror}")

    paths = sorted(os.path.join(root, name)
                   for root, _, names in os.walk(directory, onerror=unreadable)
                   for name in names if name.endswith((".yml", ".yaml")))
    if not paths:
        raise ValueError(f"alert_rules_dir {directory!r} holds no .yml or .yaml file")
    rows, groups_read = [], 0
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                documents = [document for document in yaml.safe_load_all(handle)
                             if document is not None]
        except (OSError, ValueError, yaml.YAMLError) as error:
            raise ValueError(f"{path} is unreadable as UTF-8 YAML: "
                             f"{str(error).splitlines()[0]}")
        for document in documents:
            groups = rule_groups(document, path)
            groups_read += len(groups)
            for group in groups:
                for rule in group.get("rules") or []:
                    row = unlinked_row(rule, path)
                    if row:
                        rows.append(row)
    if not groups_read:
        raise ValueError(f"alert_rules_dir {directory!r} holds no Prometheus rule group")
    return rows


def unlinked_row(rule, path):
    """The row for an alerting rule lacking an SLO or a runbook; None for one naming both, or
    for a recording rule. A field Prometheus would reject is INVALID, never a row."""
    if "alert" not in rule:
        return None
    name, annotations, labels = (rule["alert"], rule.get("annotations") or {},
                                 rule.get("labels") or {})
    if not (isinstance(name, str) and name.split() == [name]):
        raise ValueError(f"{path} holds an alert named {name!r}, not one word")
    if not (isinstance(annotations, dict) and isinstance(labels, dict)):
        raise ValueError(f"{path}'s alert {name} has labels or annotations that are not maps")
    slos = [source[key] for source in (labels, annotations) for key in SLO_KEYS
            if key in source]
    if any(not (isinstance(slo, str) and slo.split() == [slo]) for slo in slos):
        bad = next(slo for slo in slos if not (isinstance(slo, str) and slo.split() == [slo]))
        raise ValueError(f"{path}'s alert {name} names its SLO {bad!r}, not one word of "
                         "text; quote it, as YAML reads yes or 1.10 as something else")
    lacks = [what for what, present in (
        ("no SLO", slos),
        ("no runbook", any(isinstance(annotations.get(key), str) and annotations[key].strip()
                           for key in RUNBOOK_KEYS))) if not present]
    return f"{path}\t{name}\t{', '.join(lacks)}" if lacks else None


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
    environment = isolated_git_environment(TZ="Asia/Tokyo")
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
        with process_state(environment, root):
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
            write('we"ird.md')
            git("add", "--", 'runbooks/we"ird.md')
            git("commit", "-q", "-m", "quote", date="2026-01-02T12:00:00Z")
            rows = result_of(stale_runbooks, {"runbooks_dir": "runbooks"}, "2026-10-17")
            failures += report("runbooks", "a quote in a runbook's name",
                               [row for row in rows if "ird" in row],
                               ['runbooks/we"ird.md\t2026-01-02'])
            os.makedirs(os.path.join(root, "svc", "runbooks"))
            with open(os.path.join(root, "svc", "runbooks", "deep.md"), "w",
                      encoding="utf-8") as handle:
                handle.write("deep")
            git("add", "--", "svc/runbooks/deep.md")
            git("commit", "-q", "-m", "deep", date="2026-01-03T12:00:00Z")
            os.chdir(os.path.join(root, "svc"))
            failures += report("runbooks", "a project root below the repository's top level",
                               result_of(stale_runbooks, {"runbooks_dir": "runbooks"},
                                         "2026-10-17"), ["runbooks/deep.md\t2026-01-03"])
            os.chdir(root)
            shallow = os.path.join(root, "shallow")
            subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{root}", shallow],
                           env=environment, capture_output=True, check=True)
            os.chdir(shallow)
            failures += report("runbooks", "a shallow clone is refused",
                               result_of(stale_runbooks, {"runbooks_dir": "runbooks"},
                                         "2026-10-17"), "ValueError")
    return failures


ALERT_RULE_FILES = {
    "ops/alerts/api.yml": """groups:
- name: api
  rules:
  - alert: HighErrorRate
    expr: up == 0
    labels: {slo: api-availability}
    annotations: {runbook_url: "https://runbooks.example.test/api"}
  - alert: HighLatency
    expr: up == 0
    labels: {sloth_slo: api-latency}
  - alert: DiskFull
    expr: up == 0
    annotations: {summary: disk}
  - record: job:requests:rate5m
    expr: rate(requests[5m])
""",
    "ops/alerts/kustomization.yaml": "kind: Kustomization\nresources: [operator.yaml]\n",
    "ops/alerts/sloth.yaml": "version: prometheus/v1\nservice: api\nslos: []\n",
    "ops/alerts/null-rules.yml": "groups:\n- name: none-yet\n  rules:\n",
    "ops/alerts/no-groups.yml": "groups:\n",
    "ops/alerts/empty-runbook.yml": """groups:
- name: blank
  rules:
  - alert: BlankRunbook
    expr: up == 0
    annotations: {runbook_url: ""}
  - alert: SpaceRunbook
    expr: up == 0
    annotations: {runbook: "  "}
""",
    "ops/alerts/multi.yml": """groups:
- name: empty
- name: by-annotation
  rules:
  - alert: CertExpiry
    expr: up == 0
    annotations: {slo: tls-validity}
  - alert: Both
    expr: up == 0
    labels: {slo: from-labels}
    annotations: {slo: from-annotations}
---
---
groups: []
""",
    "ops/alerts/operator.yaml": """apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
spec:
  groups:
  - name: queue
    rules:
    - alert: QueueBacklog
      expr: up == 0
      annotations: {runbook: docs/runbooks/queue.md}
    - alert: QueueStalled
      expr: up == 0
  - name: thanos
    partial_response_strategy: warn
    rules: []
""",
}


def alert_rule_cases():
    failures = 0
    here = os.getcwd()
    with tempfile.TemporaryDirectory() as root:
        os.chdir(root)
        try:
            for path, text in ALERT_RULE_FILES.items():
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
            config = {"alert_rules_dir": "ops/alerts"}
            failures += report("alert-rules", "alerts naming no SLO, no runbook, or neither",
                               result_of(unlinked_alerts, config),
                               ["ops/alerts/api.yml\tHighLatency\tno runbook",
                                "ops/alerts/api.yml\tDiskFull\tno SLO, no runbook",
                                "ops/alerts/empty-runbook.yml\tBlankRunbook\tno SLO, no runbook",
                                "ops/alerts/empty-runbook.yml\tSpaceRunbook\tno SLO, no runbook",
                                "ops/alerts/multi.yml\tCertExpiry\tno runbook",
                                "ops/alerts/multi.yml\tBoth\tno runbook",
                                "ops/alerts/operator.yaml\tQueueBacklog\tno SLO",
                                "ops/alerts/operator.yaml\tQueueStalled\tno SLO, no runbook"])
            for name, text in [("a file that is not rule groups", "alerts: []\n"),
                               ("a YAML syntax error", "groups: [\n"),
                               ("a Python object tag safe_load refuses",
                                "groups: !!python/object/apply:os.system [true]\n"),
                               ("annotations as a list",
                                "groups:\n- name: g\n  rules:\n  - alert: A\n    expr: up\n"
                                "    annotations: [x]\n"),
                               ("labels as a string",
                                "groups:\n- name: g\n  rules:\n  - alert: A\n    expr: up\n"
                                "    labels: x\n"),
                               ("an alert with no name",
                                "groups:\n- name: g\n  rules:\n  - alert:\n    expr: up\n"),
                               ("an alert with no expr",
                                "groups:\n- name: g\n  rules:\n  - alert: A\n"),
                               ("an alert name with a tab",
                                "groups:\n- name: g\n  rules:\n  - alert: \"A\\tB\"\n"
                                "    expr: up\n"),
                               ("a file that is not UTF-8", b"groups: [\xe9]\n"),
                               ("a rule that is not a map",
                                "groups:\n- name: g\n  rules:\n  - alert X\n"),
                               ("a rule neither alert nor record",
                                "groups:\n- name: g\n  rules:\n  - alrt: Typo\n"),
                               ("a misspelled rules key",
                                "groups:\n- name: g\n  rule:\n  - alert: A\n    expr: up\n"),
                               ("a group that is not a map", "groups:\n- g\n"),
                               ("rules that are not a list",
                                "groups:\n- name: g\n  rules: {alert: A}\n"),
                               ("a PrometheusRule with no spec", "kind: PrometheusRule\n"),
                               ("an SLO across two lines", "groups:\n- name: g\n  rules:\n"
                                "  - alert: A\n    expr: up\n    labels: {slo: \"a\\nb\"}\n"),
                               ("an SLO YAML reads as a boolean", "groups:\n- name: g\n"
                                "  rules:\n  - alert: A\n    expr: up\n    labels: {slo: yes}\n"),
                               ("an operator-only field in a plain rule file",
                                "groups:\n- name: g\n  partial_response_strategy: warn\n"),
                               ("an impossible date", "groups:\n- name: g\n  rules:\n"
                                "  - alert: A\n    expr: up\n    labels: {d: 2026-13-01}\n")]:
                with open("ops/alerts/bad.yml", "wb") as handle:
                    handle.write(text if isinstance(text, bytes) else text.encode())
                failures += report("alert-rules", name, result_of(unlinked_alerts, config),
                                   "ValueError")
            os.remove("ops/alerts/bad.yml")
            os.makedirs("ops/alerts/locked")
            os.chmod("ops/alerts/locked", 0)
            try:
                if os.access("ops/alerts/locked", os.R_OK):
                    print("skip alert-rules: an unreadable directory needs a non-root user")
                else:
                    failures += report("alert-rules", "an unreadable subdirectory fails the read",
                                       result_of(unlinked_alerts, config), "ValueError")
            finally:
                os.chmod("ops/alerts/locked", 0o755)
                os.rmdir("ops/alerts/locked")
            os.makedirs("manifests")
            with open("manifests/kustomization.yaml", "w", encoding="utf-8") as handle:
                handle.write("kind: Kustomization\n")
            failures += report("alert-rules", "manifests holding no rule group",
                               result_of(unlinked_alerts, {"alert_rules_dir": "manifests"}),
                               "ValueError")
            with open(os.path.join(root, "project.json"), "w", encoding="utf-8") as handle:
                json.dump(config, handle)
            run = subprocess.run([sys.executable, os.path.abspath(__file__), "alert-rules",
                                  "--config", os.path.join(root, "project.json")],
                                 capture_output=True, text=True, check=False)
            failures += report("cli", "alert-rules prints its rows",
                               (run.returncode, run.stdout.splitlines()[:1]),
                               (0, ["ops/alerts/api.yml\tHighLatency\tno runbook"]))
            os.makedirs("empty")
            failures += report("alert-rules", "a directory with no rule file",
                               result_of(unlinked_alerts, {"alert_rules_dir": "empty"}),
                               "ValueError")
            failures += report("alert-rules", "a missing directory",
                               result_of(unlinked_alerts, {"alert_rules_dir": "nowhere"}),
                               "ValueError")
            failures += report("alert-rules", "alert_rules_dir none",
                               result_of(unlinked_alerts, {}), "ValueError")
        finally:
            os.chdir(here)
    return failures


def vendored_code_cases():
    """This script, the shared rules it imports, and the PyYAML it vendors keep to the Python
    3.8 grammar and import only the standard library and the vendored packages — the rule
    check_readme.py holds its own vendored parser to — so a PyYAML upgrade needing more
    fails here, not on a user's machine."""
    failures = 0
    here = os.path.dirname(os.path.abspath(__file__))
    rules = os.path.join(here, "..", "..", "..", "gates", "scripts", "project_rules.py")
    sources = [os.path.abspath(__file__), rules] + sorted(
        os.path.join(root, name) for root, _, names in os.walk(YAML_VENDOR)
        for name in names if name.endswith(".py"))
    allowed = {"project_rules", "check_readme"} | {entry for vendor in (YAML_VENDOR, MARKDOWN_VENDOR)
                                   for entry in os.listdir(vendor)
                                   if os.path.isdir(os.path.join(vendor, entry))}
    syntax_errors, foreign = foreign_code(sources, allowed)
    failures += report("vendored", "parses with the Python 3.8 grammar", syntax_errors, [])
    if foreign is None:
        print("skip vendored: stdlib-only imports need Python 3.10+ to list the standard library")
    else:
        failures += report("vendored", "imports only the standard library and _vendor/",
                           foreign, [])
    # check_readme.py keeps its own copy of the import walker, so readme-docs works alone;
    # this pins the two copies to one answer.
    readme_scripts = os.path.join(here, "..", "..", "readme-docs", "scripts")
    vendored(readme_scripts)
    import ast
    import check_readme
    from project_rules import imports_of
    sample = ast.parse("import os, yaml.nodes\nfrom markdown_it import x\nfrom . import y\n")
    failures += report("vendored", "check_readme.py's import walker agrees with the shared one",
                       check_readme.imports_of(sample), imports_of(sample))
    with tempfile.TemporaryDirectory() as directory:
        for name, text, expected in [
                ("a 3.10 match statement is caught",
                 "match x:\n    case 1:\n        pass\n", ("syntax", True)),
                ("a third-party import is caught", "import requests\n", ("foreign", True)),
                ("a file no Python parses is one error, not a crash", "x = = 1\n",
                 ("syntax", True)),
                ("vendored, relative, and stdlib imports pass",
                 "import yaml\nfrom markdown_it import MarkdownIt\nfrom . import sibling\n"
                 "import os\n", ("clean", True))]:
            path = os.path.join(directory, "fixture.py")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            errors, imports = foreign_code([path], allowed)
            if expected[0] == "foreign" and imports is None:
                print(f"skip vendored: {name} needs Python 3.10+")
                continue
            if expected[0] == "clean" and imports is None:
                found = not errors
            else:
                found = {"syntax": len(errors) == 1, "foreign": imports == ["requests"],
                         "clean": not errors and imports == []}[expected[0]]
            failures += report("vendored", name, found, True)
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
            failures += cli_case(script, name, [*arguments, "--config", config],
                                 expected_output, expected_exit, input=stdin)
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
    failures += alert_rule_cases()
    failures += vendored_code_cases()
    failures += cli_cases()
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    subcommands = {name: commands.add_parser(name)
                   for name in ("config", "alerts", "runbooks", "routes", "share", "drift",
                                "alert-rules")}
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
        elif args.command == "alert-rules":
            rows = unlinked_alerts(config)
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
