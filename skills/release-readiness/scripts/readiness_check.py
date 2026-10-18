#!/usr/bin/env python3
"""The release gates' deterministic checks, so no skill applies them by eye. Standard library
only, but for the CommonMark parser project_rules.fence_split loads.

Called by skills/release-readiness/SKILL.md (Steps 1 to 4, 7), skills/release/SKILL.md
(Steps 1 to 5), and, for its maintenance discipline keys, skills/maintenance-review/SKILL.md
(Step 1). The project.json rules it shares with the other scripts are in
gates/scripts/project_rules.py.

    readiness_check.py version --new X.Y.Z [--last vA.B.C]
        `ok` when X.Y.Z is MAJOR.MINOR.PATCH and, with --last, greater in SemVer precedence
    readiness_check.py criteria --config PATH < DESCRIPTION
        one line per `- AC<n>:` under `## Acceptance criteria`: `<AC> <tier> <evidence> ok`,
        or a problem in place of ok — `no-tag`, `undeclared-tier` — and `no-criteria` alone
        when the section is missing or empty; exit 1 on any problem
    readiness_check.py note --summary PATH --version vX.Y.Z
        prints the readiness note for that summary: version, SHA-256, last two lines
    readiness_check.py verify --summary PATH --version vX.Y.Z [--require-pass] < NOTE
        `ok` when the note on stdin is exactly the one `note` builds for the summary now
    readiness_check.py nfrs --key KEY < DESCRIPTION
        one `<KEY> NFR<n>` line per `- NFR<n>:` under `## Non-functional requirements`
    readiness_check.py settle --nfrs-file PATH [--exceptions PATH] --today YYYY-MM-DD < OUTPUT
        one tab-separated `<KEY> NFR<n>`, `pass|excepted|fail`, `<why>` line per NFR, reading the
        nfr_test_command output on stdin; exit 1 when any NFR is fail
    readiness_check.py excepted --rule RULE --exceptions PATH --today YYYY-MM-DD
        `ok` when an unexpired, complete register row's Rule is exactly RULE
    readiness_check.py scope --summary PATH --range RANGE --keys K1,K2
    readiness_check.py commit --summary PATH --head SHA
    readiness_check.py hash PATH                      prints the file's SHA-256
    readiness_check.py artifact --path PATH --sha256-file PATH
    readiness_check.py notes-headings --notes PATH [--flag-keys K1,K2]
        with keys, also a `- <KEY>: <flag>` line per key under `## Remote flags`
    readiness_check.py release-dir --value VALUE
        each but hash prints `ok`, or INVALID/MISMATCH and exits 1
    readiness_check.py disciplines --config PATH [--gate readiness|release|maintenance]
        `ok`, or one INVALID line per unknown discipline, or per key a named discipline needs
        at that gate that is absent, none, a placeholder, or malformed
    readiness_check.py oldest-devices --config PATH
        one `<os> <version>` line per OS in device_matrix, its lowest version
    readiness_check.py thresholds --config PATH
        the model_eval_thresholds pairs, one `<metric> <minimum>` line each
    readiness_check.py sensitive-paths --config PATH --range RANGE
        each path changed in RANGE matching a security_sensitive_paths glob
    readiness_check.py error-budget < OUTPUT
        `ok <n>`, or `spent <n>` and exit 1 when the one number printed is 0 or below
    readiness_check.py --self-test     runs every case below; exit 0 only if each one matches

Exit 1 is a failed check, printed to standard error as `INVALID: <what>` or `MISMATCH: <what>`,
so standard output holds only a result; exit 2 is usage. `verification_tiers` is read as
tier names separated by `·`, commas, or semicolons, each optionally in backticks and followed
by a note in parentheses; `and` and `or` are joiners, and names compare without case.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

# Importing writes no __pycache__ into the plugin's tree.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "write-tickets", "scripts"))
from lint_draft import NFR_SECTION, VERIFY_TAG  # noqa: E402  what write-tickets writes
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "gates", "scripts"))
from project_rules import (BARE_FRAGMENT, DECIMAL, PLACEHOLDER, REGISTER_COLUMNS,  # noqa: E402
                           check_command, check_repo_path, complete_register_row,
                           is_register_header,
                           fence_split, is_unset, json_number,
                           markdown_value,
                           named_disciplines,
                           positive_int, read_config as load_config, report,
                           single_number)
from project_rules import error_of as _error, result_of as _result  # noqa: E402  test helpers

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
# A criterion's tag ends its line, as lint_draft.py's AC pattern requires, so a tag quoted in
# the criterion's own wording is never read as its tag; a code span's closing backtick may follow.
BRACKET_TAG = re.compile(VERIFY_TAG + r"`?\s*$")
# Jira's Markdown conversion turns a tag written outside a code span into \verify: ... \.
# Its evidence may hold Jira's own escapes, such as \_ in a path; they are undone below.
ESCAPED_TAG = re.compile(r"\\verify:\s*([^@\\\s][^@\\]*?)\s*@\s*(\S.*?)\s*\\\s*$")
REVIEW = re.compile(r"^Reviewed-by: product_owner .+ \d{4}-\d{2}-\d{2}(, relayed by .+)?$")
GATE = re.compile(r"^Gate: (PASS|FAIL)$")


def check_version(new, last=None):
    """Raise ValueError unless `new` is MAJOR.MINOR.PATCH and above `last` (a vX.Y.Z tag)."""
    match = SEMVER.fullmatch(new)
    if not match:
        raise ValueError(f"{new!r} is not MAJOR.MINOR.PATCH")
    if last:
        previous = SEMVER.fullmatch(last[1:]) if last.startswith("v") else None
        if not previous:
            raise ValueError(f"last tag {last!r} is not vMAJOR.MINOR.PATCH")
        if tuple(map(int, match.groups())) <= tuple(map(int, previous.groups())):
            raise ValueError(f"{new} is not greater than {last}")


def declared_tiers(config_path):
    value = load_config(config_path).get("verification_tiers", "")
    # A tier's note in parentheses may hold commas or parentheses of its own; drop every note,
    # innermost first, before splitting on the separators and the joiners.
    plain = value if isinstance(value, str) else ""
    while re.search(r"\([^()]*\)", plain):
        plain = re.sub(r"\([^()]*\)", "", plain)
    plain = plain.replace("`", "")
    tiers = {" ".join(part.split()).lower()
             for part in re.split(r"[·,;]|\b(?:and|or)\b", plain, flags=re.I)} - {""}
    if not tiers:
        raise ValueError("verification_tiers declares no tiers")
    return tiers


def section_lines(description, heading, kind):
    """("item", id, line) for each `- <kind><n>:` line under `## <heading>`, ("stray", id) for
    one in another list form, and a final ("unclosed",) when a code fence never closes.
    Fenced lines are skipped; a fence closes only on a marker at least as long (CommonMark)."""
    inside = False
    item = re.compile(rf"^-\s+({kind}\d+):")
    stray = re.compile(rf"^\s*(?:[-*]|\d+\.)\s+({kind}\d+):")
    rows, unclosed = fence_split(description)
    for line, fenced in rows:
        if fenced:
            continue
        if re.match(r"^#{1,6}\s", line):
            inside = re.match(rf"^##\s+{heading}\s*$", line) is not None
            continue
        if not inside:
            continue
        found = item.match(line)
        if found:
            yield ("item", found.group(1), line)
        elif stray.match(line):
            yield ("stray", stray.match(line).group(1))
    if unclosed:
        yield ("unclosed",)


def criteria(description, tiers):
    """[(ac, tier, evidence, status)] for the acceptance-criteria section, or no-criteria."""
    rows = []
    for entry in section_lines(description, "Acceptance criteria", "AC"):
        if entry[0] == "unclosed":
            rows.append(("-", "-", "-", "unclosed-fence"))
            continue
        if entry[0] == "stray":
            rows.append((entry[1], "-", "-", "not-in-the-ac-form"))
            continue
        # Jira may also escape a bracket tag's brackets as \[ and \].
        line = entry[2].replace("\\[", "[").replace("\\]", "]")
        tag = BRACKET_TAG.search(line) or ESCAPED_TAG.search(line)
        if not tag:
            rows.append((entry[1], "-", "-", "no-tag"))
            continue
        tier = " ".join(tag.group(1).split())
        evidence = re.sub(r"\\(.)", r"\1", tag.group(2).strip())
        rows.append((entry[1], tier, evidence,
                     "ok" if tier.lower() in tiers else "undeclared-tier"))
    return rows or [("-", "-", "-", "no-criteria")]


def build_note(summary_path, version):
    """The note text, or raise ValueError when the summary's last two lines are not its
    review and verdict."""
    with open(summary_path, "rb") as handle:
        data = handle.read()
    try:
        lines = [line.rstrip() for line in data.decode("utf-8").rstrip().splitlines()]
    except UnicodeDecodeError:
        raise ValueError("summary is not UTF-8")
    if len(lines) < 2:
        raise ValueError("summary has fewer than two lines")
    review, gate = lines[-2:]
    if not REVIEW.match(review):
        raise ValueError("the line before Gate: is not a Reviewed-by: product_owner line")
    if not GATE.match(gate):
        raise ValueError("the last line is not Gate: PASS or Gate: FAIL")
    digest = hashlib.sha256(data).hexdigest()
    return f"Release-readiness: {version}\nSummary-SHA256: {digest}\n{review}\n{gate}\n"


def verify_note(summary_path, version, note, require_pass=False):
    expected = build_note(summary_path, version)
    if note.rstrip() != expected.rstrip():
        raise ValueError("the note does not match the summary as it is now")
    if require_pass and not expected.rstrip().endswith("Gate: PASS"):
        raise ValueError("the summary's verdict is not Gate: PASS")


NOTES_HEADINGS = ("## Changes", "## Migrations", "## Known issues", "## Rollback")
SCOPE = re.compile(r"^Scope: (\S+) — (\d+) tickets?: (.*)$")


def nfrs(description, key):
    """(`<KEY> NFR<n>` lines, problems) for the non-functional requirements section. A
    problem — an NFR in another list form, or an unclosed fence — means an NFR may be lost."""
    found, problems = [], []
    for entry in section_lines(description, NFR_SECTION, "NFR"):
        if entry[0] == "item":
            found.append(f"{key} {entry[1]}")
        elif entry[0] == "stray":
            problems.append(f"{key} {entry[1]} is not in the `- NFR<n>:` form")
        else:
            problems.append(f"{key}'s description has an unclosed code fence")
    return found, problems


def exceptions(path, today):
    """{Rule: Expiry} for every unexpired, complete row in a register table, in the format
    gates/exceptions.md defines; complete_register_row says which rows record one."""
    if not path:
        return {}
    with open(path, encoding="utf-8") as handle:
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in handle if line.lstrip().startswith("|")]
    if not rows or not is_register_header(rows[0]):
        raise ValueError("the exceptions register's header is not "
                         + " | ".join(REGISTER_COLUMNS))
    rule, expiry = 0, REGISTER_COLUMNS.index("Expiry")
    return {row[rule]: row[expiry] for row in rows[1:]
            if complete_register_row(row) and row[expiry] >= today}


def settle(in_scope, output, excepted_rules):
    """[(nfr, status, why)]: pass only on exactly one `<nfr> pass` line and no other line."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    settled = []
    # Two Stories under one Epic name its NFRs twice; each is settled once.
    for nfr in dict.fromkeys(in_scope):
        own = [line for line in lines if line == nfr or line.startswith(nfr + " ")]
        if own == [f"{nfr} pass"]:
            settled.append((nfr, "pass", "one pass line"))
            continue
        why = ("no result" if not own else "a fail line" if own == [f"{nfr} fail"]
               else "lines in another form or more than one")
        if nfr in excepted_rules:
            settled.append((nfr, "excepted", f"{why}; excepted until {excepted_rules[nfr]}"))
        else:
            settled.append((nfr, "fail", why))
    return settled


def header(summary_path):
    """The summary's lines before its first `## ` section: what it quotes from PRs comes
    later, so a quoted `Commit:` or `Scope:` line is never read as its own."""
    with open(summary_path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    end = next((n for n, line in enumerate(lines) if line.startswith("## ")), len(lines))
    return lines[:end]


def check_excepted(rule, register, today):
    if rule not in exceptions(register, today):
        raise ValueError(f"no unexpired, complete register row has Rule {rule!r}")


def check_scope(summary_path, scope_range, keys):
    lines = [SCOPE.match(line.rstrip()) for line in header(summary_path)]
    found = [match for match in lines if match]
    if len(found) != 1:
        raise ValueError("the summary has no single Scope: line")
    recorded = [key.strip() for key in found[0].group(3).split(",") if key.strip()]
    count = int(found[0].group(2))
    keys = [key.strip() for key in keys if key.strip()]
    if count != len(recorded):
        raise ValueError("the summary's Scope: count does not match its keys")
    if found[0].group(1) != scope_range or sorted(recorded) != sorted(keys):
        raise ValueError("the scope differs from the summary's Scope: line")


def check_commit(summary_path, head):
    commits = [line.rstrip()[len("Commit: "):] for line in header(summary_path)
               if line.startswith("Commit: ")]
    if commits != [head]:
        raise ValueError("the summary's Commit: is not HEAD")


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def check_artifact(path, recorded_path):
    with open(recorded_path, encoding="utf-8") as handle:
        recorded = handle.read().strip()
    if sha256(path) != recorded:
        raise ValueError("the artifact's SHA-256 is not the one recorded at build time")


def check_notes(notes_path, flag_keys=None):
    """The four headings, and with `flag_keys` (comma-separated) a Remote flags line each."""
    with open(notes_path, encoding="utf-8") as handle:
        lines = {line.rstrip() for line in handle}
    missing = [heading for heading in NOTES_HEADINGS if heading not in lines]
    if missing:
        raise ValueError(f"the notes lack {', '.join(missing)}")
    if flag_keys is not None:
        check_flags(notes_path, [key.strip() for key in flag_keys.split(",") if key.strip()])


def check_release_dir(value):
    check_repo_path("release_dir", value)


# The keys each named discipline needs, per gate: Appendix B's Testing addenda run at
# readiness, its Deployment addenda at release, its Maintenance addenda at maintenance-review.
# embedded's release section is a question.
GATE_KEYS = {
    "readiness": {"data-ml": ("data_quality_command", "model_eval_command",
                              "model_eval_thresholds"),
                  "mobile": ("device_matrix", "device_test_command"),
                  "embedded": ("hil_test_command",)},
    "release": {"security": ("security_sensitive_paths",),
                "mobile": ("api_compat_command", "min_supported_app_version"),
                "sre": ("error_budget_command",)},
    "maintenance": {"security": ("patch_sla_days",),
                    "data-ml": ("drift_check_command", "drift_threshold"),
                    "sre": ("alert_rules_dir",)},
}
DOTTED = r"\d+(?:\.\d+)*"
DEVICE = re.compile(rf"^({BARE_FRAGMENT}) ({DOTTED})$")
THRESHOLD = re.compile(rf"^({BARE_FRAGMENT}) ({DECIMAL})$")
FLAGS_HEADING = "## Remote flags"


def device_matrix(config):
    value = config.get("device_matrix")
    if not (isinstance(value, list) and value
            and all(isinstance(entry, str) and DEVICE.fullmatch(entry) for entry in value)):
        raise ValueError("device_matrix is not a non-empty list of `<os> <version>` entries, "
                         "the version dotted digits")
    return [DEVICE.fullmatch(entry).groups() for entry in value]


def model_thresholds(config):
    value = config.get("model_eval_thresholds")
    if not (isinstance(value, list) and value
            and all(isinstance(entry, str) and THRESHOLD.fullmatch(entry) for entry in value)):
        raise ValueError("model_eval_thresholds is not a non-empty list of `<metric> <minimum>` "
                         "pairs, the minimum a decimal number")
    metrics = [THRESHOLD.fullmatch(entry).group(1).lower() for entry in value]
    if len(set(metrics)) != len(metrics):
        raise ValueError("model_eval_thresholds names a metric twice")
    return value


def sensitive_globs(config):
    value = config.get("security_sensitive_paths")
    if is_unset(value) or not isinstance(value, str):
        raise ValueError("security_sensitive_paths is not a space-separated list of globs")
    unsupported = [pattern for pattern in value.split()
                   if pattern.startswith("!") or re.search(r"[\[\]\\]", pattern)]
    if unsupported:
        raise ValueError(f"security_sensitive_paths holds {', '.join(unsupported)}: CODEOWNERS "
                         "supports no `!` negation, `[ ]` ranges, or `\\` escapes")
    return value.split()


def owners_pathspec(pattern):
    """A CODEOWNERS pattern as git `:(glob)` pathspecs, by CODEOWNERS' rules: a pattern with
    no `/` except a trailing one matches at any depth, and a leading `/` anchors to the root.
    A literal name names a file or a directory, and a glob pathspec matches only whole paths,
    so it also matches everything below a directory of that name; a trailing `/` names only
    that. A pattern holding a `/` whose last segment holds a wildcard matches only at that
    level, as CODEOWNERS' `docs/*` matches `docs/a.md` but not `docs/sub/b.md`; a slash-free
    one such as `*secret*` still matches at any depth and below."""
    core = pattern.rstrip("/")
    spec = core.lstrip("/") if "/" in core else f"**/{core}"
    below = f":(glob){spec}/**"
    if pattern.endswith("/"):
        return [below]
    if "/" in core and re.search(r"[*?]", core.rsplit("/", 1)[-1]):
        return [f":(glob){spec}"]
    return [f":(glob){spec}", below]


def check_min_version(config):
    value = config.get("min_supported_app_version")
    if not (isinstance(value, str) and re.fullmatch(DOTTED, value)):
        raise ValueError("min_supported_app_version is not dotted digits")


FORMATS = {"device_matrix": device_matrix, "model_eval_thresholds": model_thresholds,
           "security_sensitive_paths": sensitive_globs,
           "min_supported_app_version": check_min_version,
           "patch_sla_days": lambda config: positive_int("patch_sla_days",
                                                         config.get("patch_sla_days")),
           "alert_rules_dir": lambda config: check_repo_path("alert_rules_dir",
                                                             config.get("alert_rules_dir")),
           "drift_threshold": lambda config: json_number("drift_threshold",
                                                         config.get("drift_threshold"))}


def discipline_problems(config_path, gate=None):
    """Every problem with `disciplines` and, for a gate, with each key a named discipline
    needs there: absent, `none`, blank, a README placeholder, or not in its format."""
    config = load_config(config_path)
    try:
        named = named_disciplines(config)
    except ValueError as error:
        return [str(error)]
    problems = []
    for discipline in named:
        for key in GATE_KEYS.get(gate, {}).get(discipline, ()):
            value = config.get(key)
            if is_unset(value):
                problems.append(f"{key} is absent, none, blank, or a placeholder, and "
                                f"{discipline} needs it")
            elif key in FORMATS:
                try:
                    FORMATS[key](config)
                except ValueError as error:
                    problems.append(str(error))
            else:
                try:
                    check_command(key, value)
                except ValueError as error:
                    problems.append(str(error))
    return problems


def oldest_devices(config):
    """`<os> <version>` for each OS's lowest version, OSes in first-appearance order and
    compared without case, each line as its matrix entry spells it."""
    oldest = {}
    for system, version in device_matrix(config):
        key = tuple(int(part) for part in version.split("."))
        if system.lower() not in oldest or key < oldest[system.lower()][0]:
            oldest[system.lower()] = (key, f"{system} {version}")
    return [entry for _, entry in oldest.values()]


def sensitive_paths(config_path, scope_range):
    """Paths changed in the range that match a security_sensitive_paths pattern, as CODEOWNERS
    matches. A range with no `..` is a first release, diffed from the empty tree."""
    globs = sensitive_globs(load_config(config_path))
    if not scope_range or scope_range.startswith("-"):
        raise ValueError(f"range {scope_range!r} is not a revision range")
    root = os.path.dirname(os.path.dirname(os.path.abspath(config_path)))

    def git(*arguments):
        run = subprocess.run(["git", "-c", "core.quotePath=false", *arguments], cwd=root,
                             capture_output=True, text=True, check=False)
        if run.returncode != 0:
            raise ValueError(f"git {arguments[0]} failed: {run.stderr.strip()}")
        return run.stdout

    if ".." in scope_range:
        revisions = [scope_range]
    else:
        revisions = [git("hash-object", "-t", "tree", "/dev/null").strip(), scope_range]
    output = git("diff", "--no-renames", "--name-only", "-z", *revisions, "--",
                 *[spec for pattern in globs for spec in owners_pathspec(pattern)])
    return [path for path in output.split("\0") if path]


def error_budget(output):
    """("ok" or "spent", the number) from error_budget_command's output: exactly one line
    holding one decimal number. At 0 or below the budget is spent."""
    value = single_number(output, "error_budget_command")
    return ("ok" if float(value) > 0 else "spent"), value


def check_flags(notes_path, keys):
    """Each key has a `- <KEY>: <flag>` line under `## Remote flags`, the flag no README
    placeholder."""
    with open(notes_path, encoding="utf-8") as handle:
        lines = [line.rstrip() for line in handle]
    if FLAGS_HEADING not in lines:
        raise ValueError(f"the notes lack {FLAGS_HEADING}")
    section = []
    for line in lines[lines.index(FLAGS_HEADING) + 1:]:
        if re.match(r"^#{1,6}\s", line):
            break
        section.append(line)
    def names(line, key):
        return (re.match(rf"^- {re.escape(key)}: \S", line) is not None
                and not PLACEHOLDER.match(markdown_value(line.split(": ", 1)[1])))

    missing = [key for key in keys if not any(names(line, key) for line in section)]
    if missing:
        raise ValueError(f"{FLAGS_HEADING} has no line for {', '.join(missing)}")


def scaffold_builder_output(scaffold, summary, version):
    """Run the note builder the release eval's scaffold inlines, so the two cannot drift."""
    text = open(scaffold, encoding="utf-8").read()
    found = re.search(r"<<'PY'\n(.*?)\nPY\n", text, re.S)
    if not found:
        return "no <<'PY' builder in the scaffold"
    builder = found.group(1)
    run = subprocess.run([sys.executable, "-", summary, version], input=builder,
                         capture_output=True, text=True, check=True)
    return run.stdout


SUMMARY = ("# Test summary — v1.0.0\n\nCommit: abc\n\n"
           "Reviewed-by: product_owner pat 2026-10-16\nGate: PASS\n")

VERSION_CASES = [
    ("a first release", "1.0.0", None, "ok"),
    ("a patch above the last", "1.0.1", "v1.0.0", "ok"),
    ("a major above a higher minor", "2.0.0", "v1.9.9", "ok"),
    ("numeric, not string, order", "1.10.0", "v1.9.0", "ok"),
    ("equal to the last", "1.0.0", "v1.0.0", "ValueError"),
    ("below the last", "1.0.0", "v2.0.0", "ValueError"),
    ("a leading v", "v1.0.0", None, "ValueError"),
    ("two parts", "1.0", None, "ValueError"),
    ("a leading zero", "1.01.0", None, "ValueError"),
    ("a pre-release suffix", "1.0.0-rc1", None, "ValueError"),
    ("a trailing newline", "1.0.0\n", None, "ValueError"),
    ("a last tag that is not a version", "1.0.0", "vendor-x", "ValueError"),
    ("a last tag with no v", "1.0.1", "1.0.0", "ValueError"),
]

TIERS = {"ci", "inspection", "eval", "manual qa"}
CRITERIA_CASES = [
    ("a bracket tag", "## Acceptance criteria\n\n- AC1: x [verify: ci @ .github]\n",
     [("AC1", "ci", ".github", "ok")]),
    ("a code-span tag", "## Acceptance criteria\n- AC1: x `[verify: eval @ evals]`\n",
     [("AC1", "eval", "evals", "ok")]),
    ("Jira's escaped tag", "## Acceptance criteria\n- AC1: x \\verify: inspection @ skills\\\n",
     [("AC1", "inspection", "skills", "ok")]),
    ("an undeclared tier", "## Acceptance criteria\n- AC1: x [verify: automated @ t]\n",
     [("AC1", "automated", "t", "undeclared-tier")]),
    ("no tag", "## Acceptance criteria\n- AC1: x\n", [("AC1", "-", "-", "no-tag")]),
    ("a malformed tag", "## Acceptance criteria\n- AC1: x [verify: ci]\n",
     [("AC1", "-", "-", "no-tag")]),
    ("no heading", "## Behavior\n- AC1: x [verify: ci @ y]\n",
     [("-", "-", "-", "no-criteria")]),
    ("a heading with no criteria", "## Acceptance criteria\n\n## Touch points\n- a\n",
     [("-", "-", "-", "no-criteria")]),
    ("a quoted tag before the real one",
     "## Acceptance criteria\n- AC1: lines read `[verify: ci @ x]` tags \\verify: bogus @ y\\\n",
     [("AC1", "bogus", "y", "undeclared-tier")]),
    ("a tag that is not at the end", "## Acceptance criteria\n- AC1: [verify: ci @ x] then text\n",
     [("AC1", "-", "-", "no-tag")]),
    ("a multi-word tier", "## Acceptance criteria\n- AC1: x [verify: manual QA @ y]\n",
     [("AC1", "manual QA", "y", "ok")]),
    ("one word of a multi-word tier", "## Acceptance criteria\n- AC1: x [verify: QA @ y]\n",
     [("AC1", "QA", "y", "undeclared-tier")]),
    ("Jira's escapes inside evidence",
     "## Acceptance criteria\n- AC1: x \\verify: ci @ tests/foo\\_bar.py\\\n",
     [("AC1", "ci", "tests/foo_bar.py", "ok")]),
    ("a tier in another case", "## Acceptance criteria\n- AC1: x [verify: Inspection @ y]\n",
     [("AC1", "Inspection", "y", "ok")]),
    ("Jira's escaped brackets", "## Acceptance criteria\n- AC1: x \\[verify: ci @ y\\]\n",
     [("AC1", "ci", "y", "ok")]),
    ("a tilde fence is skipped",
     "## Acceptance criteria\n~~~\n- AC9: x\n~~~\n- AC1: x [verify: ci @ y]\n",
     [("AC1", "ci", "y", "ok")]),
    ("an unclosed fence with no final newline is a problem",
     "## Acceptance criteria\n- AC1: x [verify: ci @ y]\n```\n- AC2: z [verify: ci @ y]",
     [("AC1", "ci", "y", "ok"), ("-", "-", "-", "unclosed-fence")]),
    ("an unclosed fence is a problem",
     "## Acceptance criteria\n- AC1: x [verify: ci @ y]\n```\n- AC2: z\n",
     [("AC1", "ci", "y", "ok"), ("-", "-", "-", "unclosed-fence")]),
    ("criteria in other list forms",
     "## Acceptance criteria\n  - AC4: x [verify: ci @ y]\n* AC5: x\n1. AC6: x\n",
     [("AC4", "-", "-", "not-in-the-ac-form"), ("AC5", "-", "-", "not-in-the-ac-form"),
      ("AC6", "-", "-", "not-in-the-ac-form")]),
    ("a shorter fence does not close a longer one",
     "## Acceptance criteria\n````\n```\n- AC9: x\n````\n- AC1: x [verify: ci @ y]\n",
     [("AC1", "ci", "y", "ok")]),
    ("a fenced comment does not end the section",
     "## Acceptance criteria\n- AC1: x [verify: ci @ y]\n```\n# not a heading\n```\n- AC2: z\n",
     [("AC1", "ci", "y", "ok"), ("AC2", "-", "-", "no-tag")]),
    ("a marker indented four spaces is code, not a fence",
     "## Acceptance criteria\n\n    ```\n    code\n\n- AC1: x [verify: ci @ y]\n",
     [("AC1", "ci", "y", "ok")]),
    ("a backtick in the opener's info string is no fence",
     "## Acceptance criteria\n```x`y\n- AC1: x [verify: ci @ y]\n", [("AC1", "ci", "y", "ok")]),
    ("a closed fence in a blockquote",
     "## Acceptance criteria\n- AC1: x [verify: ci @ y]\n\n> ```\n> code\n> ```\n",
     [("AC1", "ci", "y", "ok")]),
    ("a closed fence in a nested list item",
     "## Acceptance criteria\n- AC1: x [verify: ci @ y]\n  - b\n    ```\n    code\n    ```\n",
     [("AC1", "ci", "y", "ok")]),
    ("a closer with an info string closes nothing",
     "## Acceptance criteria\n```\n```x\n```\n- AC1: x [verify: ci @ y]\n",
     [("AC1", "ci", "y", "ok")]),
    ("lone carriage returns end lines as markdown-it reads them",
     "## Acceptance criteria\r```\r- AC9: x\r```\r- AC1: x [verify: ci @ y]\r",
     [("AC1", "ci", "y", "ok")]),
    ("the section ends at the next heading",
     "## Acceptance criteria\n- AC1: x [verify: ci @ y]\n## Out of scope\n- AC9: z\n",
     [("AC1", "ci", "y", "ok")]),
]


def self_test():
    failures = 0
    for name, new, last, expected in VERSION_CASES:
        try:
            check_version(new, last)
            got = "ok"
        except ValueError:
            got = "ValueError"
        failures += report("version", name, got, expected)
    for name, description, expected in CRITERIA_CASES:
        failures += report("criteria", name, criteria(description, TIERS), expected)
    with tempfile.TemporaryDirectory() as directory:
        config = os.path.join(directory, "project.json")
        with open(config, "w", encoding="utf-8") as handle:
            json.dump({"verification_tiers": "ci (a named step in ci.yml) · self-test (a hook "
                                              "self-test case, a fixture, or a case) · eval · "
                                              "inspection (out-of-band: Rob reads it)"}, handle)
        failures += report("criteria", "tiers read from verification_tiers prose",
                           declared_tiers(config), {"ci", "self-test", "eval", "inspection"})
        for name, value, expected in [
                ("joiners and a missing last name", "unit, integration, and manual",
                 {"unit", "integration", "manual"}),
                ("backticked tiers with notes", "`unit` (XCTest); `UI` (XCUITest)",
                 {"unit", "ui"}),
                ("a multi-word tier stays whole", "unit, manual QA, and integration",
                 {"unit", "manual qa", "integration"}),
                ("and as the only joiner", "unit and integration", {"unit", "integration"}),
                ("or as the only joiner", "unit or manual", {"unit", "manual"}),
                ("a nested note", "ci (note (nested)) · eval", {"ci", "eval"}),
                ("no tiers", "", "ValueError"), ("a non-string value", ["ci"], "ValueError")]:
            path = os.path.join(directory, "tiers.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"verification_tiers": value}, handle)
            failures += report("criteria", name, _result(declared_tiers, path), expected)

        def summary_file(text, name="summary.md", mode="w"):
            path = os.path.join(directory, name)
            with open(path, mode) as handle:
                handle.write(text)
            return path

        good = summary_file(SUMMARY)
        note = build_note(good, "v1.0.0")
        failures += report("note", "a reviewed summary builds its note",
                           note.splitlines()[0::2], ["Release-readiness: v1.0.0",
                                                     "Reviewed-by: product_owner pat 2026-10-16"])
        for name, text, mode in [
                ("a one-line summary", "Gate: PASS\n", "w"),
                ("no review line", "# x\nCommit: a\nGate: PASS\n", "w"),
                ("no verdict line", "# x\nReviewed-by: product_owner pat 2026-10-16\n", "w"),
                ("a summary that is not UTF-8", b"\xff\xfe\nReviewed-by: x\nGate: PASS\n", "wb")]:
            failures += report("note", name, _error(build_note, summary_file(text, "bad.md", mode),
                                                    "v1.0.0"), "ValueError")
        failures += report("note", "trailing whitespace and CRLF are stripped",
                           build_note(summary_file(SUMMARY.replace("\n", " \r\n"), "crlf.md"),
                                      "v1.0.0").splitlines()[2:],
                           ["Reviewed-by: product_owner pat 2026-10-16", "Gate: PASS"])
        failures += report("verify", "the note it built matches",
                           _error(verify_note, good, "v1.0.0", note, True), "ok")
        failures += report("verify", "a note for another version",
                           _error(verify_note, good, "v1.0.1", note), "ValueError")
        edited = summary_file(SUMMARY.replace("abc", "abd"), "edited.md")
        failures += report("verify", "a summary edited after the note",
                           _error(verify_note, edited, "v1.0.0", note), "ValueError")
        failures += report("verify", "no note", _error(verify_note, good, "v1.0.0", ""),
                           "ValueError")
        failing = summary_file(SUMMARY.replace("Gate: PASS", "Gate: FAIL"), "fail.md")
        failures += report("verify", "a FAIL summary when PASS is required",
                           _error(verify_note, failing, "v1.0.0",
                                  build_note(failing, "v1.0.0"), True), "ValueError")
        failures += release_checks_cases(directory, summary_file, good)
        scaffold = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                                "evals", "release-asks-before-staging", "scaffold.sh")
        failures += report("note", "the release eval's scaffold builds the same note",
                           scaffold_builder_output(scaffold, good, "v1.0.0")
                           if os.path.exists(scaffold) else "no scaffold", note)
        script = os.path.abspath(__file__)
        for name, arguments, stdin, expected_output, expected_exit in [
                ("version ok", ["version", "--new", "1.2.0", "--last", "v1.1.9"], "", "ok", 0),
                ("version below", ["version", "--new", "1.0.0", "--last", "v1.1.0"], "",
                 "INVALID: 1.0.0 is not greater", 1),
                ("a failed note writes nothing to standard output",
                 ["note", "--summary", summary_file("# x\nGate: PASS\n", "noreview.md"),
                  "--version", "v1.0.0"], "", "", 1),
                ("criteria with a config that is not an object",
                 ["criteria", "--config", summary_file("[]", "list.json")],
                 "## Acceptance criteria\n", "INVALID:", 1),
                ("criteria with a missing config",
                 ["criteria", "--config", os.path.join(directory, "absent.json")],
                 "## Acceptance criteria\n", "INVALID:", 1),
                ("verify with a missing summary",
                 ["verify", "--summary", os.path.join(directory, "absent.md"), "--version",
                  "v1.0.0"], note, "INVALID:", 1),
                ("criteria with a problem", ["criteria", "--config", config],
                 "## Acceptance criteria\n- AC1: x [verify: automated @ t]\n",
                 "AC1\tautomated\tt\tundeclared-tier", 1),
                ("criteria all ok", ["criteria", "--config", config],
                 "## Acceptance criteria\n- AC1: x [verify: ci @ t]\n", "AC1\tci\tt\tok", 0),
                ("verify ok", ["verify", "--summary", good, "--version", "v1.0.0",
                               "--require-pass"], note, "ok", 0),
                ("verify mismatch", ["verify", "--summary", edited, "--version", "v1.0.0"],
                 note, "MISMATCH: the note does not match", 1),
                ("note prints the note", ["note", "--summary", good, "--version", "v1.0.0"], "",
                 "Release-readiness: v1.0.0", 0),
                ("settle exits 1 on a fail", ["settle", "--nfrs-file",
                                             summary_file("AB-1 NFR1\n", "inscope.txt"),
                                             "--today", "2026-10-16"],
                 "AB-1 NFR1 fail\n", "AB-1 NFR1\tfail", 1),
                ("settle exits 0 on a pass", ["settle", "--nfrs-file",
                                             os.path.join(directory, "inscope.txt"),
                                             "--today", "2026-10-16"],
                 "AB-1 NFR1 pass\n", "AB-1 NFR1\tpass", 0),
                ("scope mismatch", ["scope", "--summary", good, "--range", "HEAD", "--keys",
                                    "AB-1"], "", "MISMATCH: the summary has no single", 1),
                ("release-dir ok", ["release-dir", "--value", "docs/releases"], "", "ok", 0),
                ("release-dir fail", ["release-dir", "--value", "/abs"], "", "MISMATCH:", 1),
                ("hash prints the digest", ["hash", good], "", sha256(good), 0),
                ("commit mismatch", ["commit", "--summary", good, "--head", "abd"], "",
                 "MISMATCH: the summary's Commit:", 1),
                ("artifact ok", ["artifact", "--path", good, "--sha256-file",
                                 summary_file(sha256(good), "good.sha256")], "", "ok", 0),
                ("notes-headings fail", ["notes-headings", "--notes", good], "",
                 "MISMATCH: the notes lack", 1),
                ("settle with a register excepts", ["settle", "--nfrs-file",
                                                    summary_file("AB-1 NFR2\n", "two.txt"),
                                                    "--exceptions",
                                                    os.path.join(directory, "register.md"),
                                                    "--today", "2026-10-16"],
                 "AB-1 NFR2 fail\n", "AB-1 NFR2\texcepted", 0),
                ("excepted ok", ["excepted", "--rule", "AB-1 NFR2", "--exceptions",
                                 os.path.join(directory, "register.md"), "--today", "2026-10-16"],
                 "", "ok", 0),
                ("excepted missing", ["excepted", "--rule", "AB-7 not found", "--exceptions",
                                      os.path.join(directory, "register.md"), "--today",
                                      "2026-10-16"], "", "MISMATCH: no unexpired", 1),
                ("disciplines ok", ["disciplines", "--config",
                                    summary_file(json.dumps(READY), "ready.json"), "--gate",
                                    "readiness"], "", "ok", 0),
                ("disciplines names the key", ["disciplines", "--config",
                                               summary_file(json.dumps({"disciplines": ["sre"]}),
                                                            "sre.json"), "--gate", "release"],
                 "", "INVALID: error_budget_command is absent", 1),
                ("oldest-devices lists one per OS", ["oldest-devices", "--config",
                                                     os.path.join(directory, "ready.json")],
                 "", "ios 15.4", 0),
                ("thresholds lists the pairs", ["thresholds", "--config",
                                                os.path.join(directory, "ready.json")],
                 "", "precision 0.92", 0),
                ("thresholds with none set", ["thresholds", "--config",
                                              os.path.join(directory, "sre.json")],
                 "", "INVALID: model_eval_thresholds", 1),
                ("error-budget spent exits 1", ["error-budget"], "0\n", "spent 0", 1),
                ("error-budget ok", ["error-budget"], "12.5\n", "ok 12.5", 0),
                ("error-budget unreadable", ["error-budget"], "n/a\n", "INVALID:", 1),
                ("notes-headings without flags", ["notes-headings", "--notes",
                                                  summary_file("## Changes\n## Migrations\n"
                                                               "## Known issues\n## Rollback\n",
                                                               "plain.md")], "", "ok", 0),
                ("sensitive-paths lists the matching paths",
                 ["sensitive-paths", "--config", os.path.join(directory, "repo", ".claude",
                                                              "project.json"),
                  "--range", "v1.1.0..v1.2.0"], "", "src/auth/login.py", 0),
                ("notes-headings with a flag line missing",
                 ["notes-headings", "--notes", os.path.join(directory, "spaced.md"),
                  "--flag-keys", "AB-1,AB-3"], "", "MISMATCH: ## Remote flags has no line", 1),
                ("notes-headings with every flag key", ["notes-headings", "--notes",
                                                        os.path.join(directory, "spaced.md"),
                                                        "--flag-keys", "AB-1,AB-2"], "", "ok", 0),
                ("notes-headings with no Remote flags heading",
                 ["notes-headings", "--notes", os.path.join(directory, "plain.md"),
                  "--flag-keys", "AB-1"], "", "MISMATCH: the notes lack ## Remote flags", 1),
                ("nfrs exits 1 on a problem", ["nfrs", "--key", "AB-1"],
                 "## Non-functional requirements\n* NFR1: a\n", "INVALID:", 1),
                ("no subcommand is usage", [], "", "", 2)]:
            run = subprocess.run([sys.executable, script, *arguments], input=stdin,
                                 capture_output=True, text=True, check=False)
            failed = expected_output.startswith(("INVALID", "MISMATCH"))
            stream = run.stderr if failed else run.stdout
            first = (stream.strip().splitlines() or [""])[0]
            shown = first[:len(expected_output)] if expected_output else stream.strip()
            failures += report("cli", name, (shown, run.returncode),
                               (expected_output, expected_exit))
    return 1 if failures else 0


def release_checks_cases(directory, summary_file, good):
    failures = 0
    description = ("## Non-functional requirements\n\n- NFR1: p95 < 300 ms [verify: ci @ x]\n"
                   "```\n- NFR9: fenced\n```\n- NFR2: size < 1 MB\n## Acceptance criteria\n"
                   "- NFR3: not here\n")
    failures += report("nfrs", "NFR lines under their heading only",
                       nfrs(description, "AB-1"), (["AB-1 NFR1", "AB-1 NFR2"], []))
    failures += report("nfrs", "no heading", nfrs("## Behavior\n- NFR1: x\n", "AB-1"), ([], []))
    failures += report("nfrs", "an unclosed fence is a problem",
                       len(nfrs("## Non-functional requirements\n- NFR1: a\n```\n- NFR2: b\n",
                                "AB-1")[1]), 1)
    failures += report("nfrs", "NFRs in other list forms are problems",
                       len(nfrs("## Non-functional requirements\n* NFR1: a\n  - NFR2: b\n",
                                "AB-1")[1]), 2)
    register = summary_file("| Rule | Reason | Risk | Expiry | Remediation |\n| --- | --- | --- | "
                            "--- | --- |\n| AB-1 NFR2 | r | r | 2026-12-31 | t |\n"
                            "| AB-1 NFR3 | r | r | 2026-01-01 | t |\n", "register.md")
    rules = exceptions(register, "2026-10-16")
    failures += report("settle", "only unexpired rows count", rules, {"AB-1 NFR2": "2026-12-31"})
    failures += report("settle", "a row expiring today still counts",
                       exceptions(register, "2026-12-31"), {"AB-1 NFR2": "2026-12-31"})
    impossible = summary_file("| Rule | Reason | Risk | Expiry | Remediation |\n| --- | --- | "
                              "--- | --- | --- |\n| AB-1 NFR2 | r | r | 2026-02-30 | t |\n",
                              "impossible.md")
    failures += report("settle", "a row expiring on no calendar date records no exception",
                       exceptions(impossible, "2026-01-01"), {})
    partial = summary_file("| Rule | Reason | Risk | Expiry | Remediation | Owner |\n| --- | --- | "
                           "--- | --- | --- | --- |\n| AB-1 NFR2 | r | r | 2026-12-31 |\n"
                           "| AB-1 NFR3 | r | --- | 2026-12-31 | t | o |\n"
                           "| AB-1 NFR4 | r | r | 2026-12-31 | t | o |\n", "partial.md")
    failures += report("settle", "a short row and a separator cell record none; a sixth column is "
                       "allowed", exceptions(partial, "2026-01-01"), {"AB-1 NFR4": "2026-12-31"})
    in_scope = ["AB-1 NFR1", "AB-1 NFR2", "AB-1 NFR3", "AB-1 NFR4", "AB-1 NFR5"]
    output = ("AB-1 NFR1 pass\nAB-1 NFR2 fail\nAB-1 NFR3 pass\nAB-1 NFR3 fail\n"
              "AB-1 NFR5 maybe\nAB-9 NFR1 fail\nAB-1 NFR10 pass\n")
    failures += report("settle", "pass, excepted, both lines, no result, other form",
                       [row[:2] for row in settle(in_scope, output, rules)],
                       [("AB-1 NFR1", "pass"), ("AB-1 NFR2", "excepted"), ("AB-1 NFR3", "fail"),
                        ("AB-1 NFR4", "fail"), ("AB-1 NFR5", "fail")])
    failures += report("settle", "an NFR named twice is settled once",
                       len(settle(["AB-1 NFR1", "AB-1 NFR1"], "AB-1 NFR1 pass\n", set())), 1)
    failures += report("settle", "no result, excepted by a register row",
                       [row[1:] for row in settle(["AB-1 NFR2"], "", rules)],
                       [("excepted", "no result; excepted until 2026-12-31")])
    failures += report("settle", "no output: every NFR has no result",
                       [row[1:] for row in settle(["AB-1 NFR1"], "", set())],
                       [("fail", "no result")])
    partial = summary_file("| Rule | Reason | Risk | Expiry | Remediation |\n| --- | --- | --- | "
                           "--- | --- |\n| AB-1 NFR2 |  |  | 2026-12-31 |  |\n", "partial.md")
    failures += report("settle", "a row missing its reason, risk, or remediation excepts nothing",
                       exceptions(partial, "2026-10-16"), {})
    failures += report("settle", "a register with only Rule and Expiry columns", _error(
        exceptions, summary_file("| Rule | Expiry |\n| AB-1 NFR2 | 2026-12-31 |\n", "two.md"),
        "2026-10-16"), "ValueError")
    failures += report("settle", "a register with no header", _error(
        exceptions, summary_file("| a | b |\n", "noheader.md"), "2026-10-16"), "ValueError")
    scoped = summary_file("# x\nCommit: abc123\nScope: v1.0.0..HEAD — 2 tickets: AB-1, AB-2\n",
                          "scoped.md")
    failures += report("scope", "the same range and keys",
                       _error(check_scope, scoped, "v1.0.0..HEAD", ["AB-2", "AB-1"]), "ok")
    failures += report("scope", "a different range",
                       _error(check_scope, scoped, "v1.1.0..HEAD", ["AB-1", "AB-2"]), "ValueError")
    failures += report("scope", "an extra key",
                       _error(check_scope, scoped, "v1.0.0..HEAD", ["AB-1", "AB-2", "AB-3"]),
                       "ValueError")
    failures += report("scope", "keys with spaces around them",
                       _error(check_scope, scoped, "v1.0.0..HEAD", [" AB-1", "AB-2 "]), "ok")
    failures += report("scope", "a count that disagrees with the keys",
                       _error(check_scope, summary_file("Scope: HEAD — 3 tickets: AB-1, AB-2\n",
                                                        "count.md"), "HEAD", ["AB-1", "AB-2"]),
                       "ValueError")
    failures += report("scope", "one ticket, singular",
                       _error(check_scope, summary_file("Scope: HEAD — 1 ticket: AB-1\n", "one.md"),
                              "HEAD", ["AB-1"]), "ok")
    failures += report("commit", "HEAD matches", _error(check_commit, scoped, "abc123"), "ok")
    quoting = summary_file("# x\nCommit: abc123\nScope: HEAD — 1 ticket: AB-1\n\n## Known risks\n"
                           "Commit: def456\nScope: v9..HEAD — 1 ticket: AB-9\n", "quoting.md")
    failures += report("commit", "a quoted Commit: line in a later section is not read",
                       _error(check_commit, quoting, "abc123"), "ok")
    failures += report("scope", "a quoted Scope: line in a later section is not read",
                       _error(check_scope, quoting, "HEAD", ["AB-1"]), "ok")
    failures += report("commit", "another commit", _error(check_commit, scoped, "abc124"),
                       "ValueError")
    failures += report("commit", "a prefix is not HEAD", _error(check_commit, scoped, "abc"),
                       "ValueError")
    artifact = summary_file("bytes", "app.tar")
    recorded = summary_file(sha256(artifact) + "\n", "app.sha256")
    failures += report("artifact", "the recorded hash", _error(check_artifact, artifact, recorded),
                       "ok")
    summary_file("changed", "app.tar")
    failures += report("artifact", "a changed artifact",
                       _error(check_artifact, artifact, recorded), "ValueError")
    full = summary_file("# v1\n\n## Changes\n## Migrations\n## Known issues\n## Rollback\n",
                        "notes.md")
    failures += report("notes", "all four headings", _error(check_notes, full), "ok")
    failures += report("notes", "a heading missing",
                       _error(check_notes, summary_file("## Changes\n## Migrations\n## Rollback\n",
                                                        "short.md")), "ValueError")
    for name, value, expected in [("relative", "docs/releases", "ok"),
                                  ("absolute", "/tmp/releases", "ValueError"),
                                  ("whitespace", "docs/my releases", "ValueError"),
                                  ("outside the repo", "../releases", "ValueError"),
                                  ("the repo root", ".", "ValueError"),
                                  ("a nested escape", "a/../..", "ValueError"),
                                  ("a command substitution", "docs/$(id)", "ValueError"),
                                  ("a glob", "docs/*", "ValueError"),
                                  ("a separator", "docs;x", "ValueError"),
                                  ("git's own directory", ".git/releases", "ValueError"),
                                  ("an option", "-n", "ValueError"),
                                  ("none", "none", "ValueError"),
                                  ("a trailing newline", "docs\n", "ValueError"),
                                  ("None", "None", "ValueError"),
                                  ("NONE", "NONE", "ValueError"),
                                  ("not a string", ["docs"], "ValueError")]:
        failures += report("release-dir", name, _error(check_release_dir, value), expected)
    return failures + discipline_cases(directory, summary_file)


READY = {"disciplines": ["data-ml", "mobile", "embedded"],
         "data_quality_command": "dq", "model_eval_command": "me",
         "model_eval_thresholds": ["precision 0.92", "recall 0.8"],
         "device_matrix": ["ios 17.4", "ios 15.10", "android 14", "ios 15.4", "android 9"],
         "device_test_command": "dt", "hil_test_command": "hil"}
RELEASED = {"disciplines": ["security", "mobile", "embedded", "sre"],
            "security_sensitive_paths": "src/auth/** *.pem", "api_compat_command": "ac",
            "min_supported_app_version": "4.2", "error_budget_command": "eb"}
MAINTAINED = {"disciplines": ["security", "data-ml", "sre"], "patch_sla_days": 30,
              "drift_check_command": "dc", "drift_threshold": 0.25,
              "alert_rules_dir": "ops/alerts"}


def discipline_cases(directory, summary_file):
    failures = 0

    def problems(value, gate=None):
        return discipline_problems(summary_file(json.dumps(value), "disciplines.json"), gate)

    for name, value, gate, expected in [
            ("absent disciplines are []", {}, "release", []),
            ("an empty list", {"disciplines": []}, "readiness", []),
            ("every readiness key set", READY, "readiness", []),
            ("every release key set", RELEASED, "release", []),
            ("no gate checks names only", {"disciplines": ["mobile"]}, None, []),
            ("a discipline outside the gate needs nothing here", {"disciplines": ["sre"]},
             "readiness", []),
            ("an unknown discipline", {"disciplines": ["mobil"]}, None, ["disciplines"]),
            ("a discipline in another case", {"disciplines": ["Mobile"]}, None, ["disciplines"]),
            ("disciplines as a string", {"disciplines": "mobile"}, None, ["disciplines"]),
            ("a key absent", {"disciplines": ["embedded"]}, "readiness", ["hil_test_command"]),
            ("a key none", dict(READY, hil_test_command="none"), "readiness",
             ["hil_test_command"]),
            ("a key blank", dict(READY, hil_test_command="  "), "readiness", ["hil_test_command"]),
            ("a key a placeholder", dict(READY, data_quality_command="<command>"), "readiness",
             ["data_quality_command"]),
            ("a command that is not a string", dict(RELEASED, error_budget_command=["eb"]),
             "release", ["error_budget_command"]),
            ("a matrix entry with no version", dict(READY, device_matrix=["ios"]), "readiness",
             ["device_matrix"]),
            ("a matrix version with letters", dict(READY, device_matrix=["ios 17b"]),
             "readiness", ["device_matrix"]),
            ("a matrix OS that looks like an option", dict(READY, device_matrix=["-rf 1"]),
             "readiness", ["device_matrix"]),
            ("a matrix placeholder", dict(READY, device_matrix=["<os> <version>"]),
             "readiness", ["device_matrix"]),
            ("an empty matrix", dict(READY, device_matrix=[]), "readiness", ["device_matrix"]),
            ("a threshold that is not a number", dict(READY, model_eval_thresholds=["auc high"]),
             "readiness", ["model_eval_thresholds"]),
            ("a metric named twice", dict(READY, model_eval_thresholds=["auc 0.8", "auc 0.9"]),
             "readiness", ["model_eval_thresholds"]),
            ("a metric named twice in two cases",
             dict(READY, model_eval_thresholds=["auc 0.8", "AUC 0.9"]), "readiness",
             ["model_eval_thresholds"]),
            ("a key none in another case", dict(READY, hil_test_command="None "), "readiness",
             ["hil_test_command"]),
            ("sensitive paths none", dict(RELEASED, security_sensitive_paths="none"), "release",
             ["security_sensitive_paths"]),
            ("a negated sensitive path", dict(RELEASED, security_sensitive_paths="src/ !docs/"),
             "release", ["security_sensitive_paths"]),
            ("a bracket range in a sensitive path",
             dict(RELEASED, security_sensitive_paths="key[0-9].pem"), "release",
             ["security_sensitive_paths"]),
            ("a lone closing bracket", dict(RELEASED, security_sensitive_paths="key].pem"),
             "release", ["security_sensitive_paths"]),
            ("a backslash escape", dict(RELEASED, security_sensitive_paths="\\#secret"),
             "release", ["security_sensitive_paths"]),
            ("a ! inside a pattern", dict(RELEASED, security_sensitive_paths="src/a!b/"),
             "release", []),
            ("blank sensitive paths", dict(RELEASED, security_sensitive_paths=" "), "release",
             ["security_sensitive_paths"]),
            ("a minimum version with a trailing newline",
             dict(RELEASED, min_supported_app_version="4.2\n"), "release",
             ["min_supported_app_version"]),
            ("a matrix entry with a trailing newline", dict(READY, device_matrix=["ios 16\n"]),
             "readiness", ["device_matrix"]),
            ("a minimum version with letters", dict(RELEASED, min_supported_app_version="4.x"),
             "release", ["min_supported_app_version"]),
            ("every maintenance key set", MAINTAINED, "maintenance", []),
            ("a whole-number drift threshold", dict(MAINTAINED, drift_threshold=1),
             "maintenance", []),
            ("maintenance needs nothing of mobile", {"disciplines": ["mobile"]}, "maintenance",
             []),
            ("security without its SLA", {"disciplines": ["security"]}, "maintenance",
             ["patch_sla_days"]),
            ("an SLA of zero", dict(MAINTAINED, patch_sla_days=0), "maintenance",
             ["patch_sla_days"]),
            ("an SLA as a string", dict(MAINTAINED, patch_sla_days="30"), "maintenance",
             ["patch_sla_days"]),
            ("an SLA of true", dict(MAINTAINED, patch_sla_days=True), "maintenance",
             ["patch_sla_days"]),
            ("sre without its alert rules", dict(MAINTAINED, alert_rules_dir="none"),
             "maintenance", ["alert_rules_dir"]),
            ("alert rules outside the repository", dict(MAINTAINED, alert_rules_dir="../ops"),
             "maintenance", ["alert_rules_dir"]),
            ("a drift threshold as a string", dict(MAINTAINED, drift_threshold="0.25"),
             "maintenance", ["drift_threshold"]),
            ("a drift threshold of false", dict(MAINTAINED, drift_threshold=False),
             "maintenance", ["drift_threshold"]),
            ("a drift threshold in exponent form", dict(MAINTAINED, drift_threshold=1e-5),
             "maintenance", []),
            ("a drift threshold of NaN", dict(MAINTAINED, drift_threshold=float("nan")),
             "maintenance", ["drift_threshold"]),
            ("data-ml without either drift key", {"disciplines": ["data-ml"]}, "maintenance",
             ["drift_check_command", "drift_threshold"]),
            ("two keys absent are two problems", {"disciplines": ["data-ml"],
                                                  "data_quality_command": "dq"}, "readiness",
             ["model_eval_command", "model_eval_thresholds"])]:
        got = problems(value, gate)
        failures += report("disciplines", name, [problem.split()[0] for problem in got], expected)
    failures += report("devices", "the lowest version per OS, compared as numbers",
                       oldest_devices(READY), ["ios 15.4", "android 9"])
    failures += report("devices", "one OS in two cases is one OS",
                       oldest_devices({"device_matrix": ["iOS 17", "ios 15"]}), ["ios 15"])
    failures += report("devices", "a single entry", oldest_devices({"device_matrix": ["ios 16"]}),
                       ["ios 16"])
    failures += report("devices", "an invalid matrix",
                       _result(oldest_devices, {"device_matrix": "ios 16"}), "ValueError")
    for name, output, expected in [("a positive budget", "0.01\n", ("ok", "0.01")),
                                   ("zero", "0", ("spent", "0")),
                                   ("a negative budget", "-0.5\n", ("spent", "-0.5")),
                                   ("negative zero", "-0", ("spent", "-0")),
                                   ("blank", "\n", "ValueError"),
                                   ("two lines", "3\n4\n", "ValueError"),
                                   ("a percent sign", "5%\n", "ValueError"),
                                   ("not a number", "nan\n", "ValueError"),
                                   ("a word around it", "budget: 5\n", "ValueError")]:
        failures += report("error-budget", name, _result(error_budget, output), expected)
    flags = summary_file("## Changes\n## Remote flags\n\n- AB-1: new_checkout\n"
                         "- AB-2: none — a bug fix\n## Rollback\n- AB-3: x\n", "flags.md")
    failures += report("flags", "a line for every key",
                       _error(check_flags, flags, ["AB-1", "AB-2"]), "ok")
    failures += report("flags", "a key with no line",
                       _error(check_flags, flags, ["AB-1", "AB-4"]), "ValueError")
    failures += report("flags", "a line after the section does not count",
                       _error(check_flags, flags, ["AB-3"]), "ValueError")
    failures += report("flags", "a prefix of another key does not count",
                       _error(check_flags, flags, ["AB-"]), "ValueError")
    failures += report("flags", "a placeholder flag",
                       _error(check_flags, summary_file("## Remote flags\n- AB-1: <flag>\n",
                                                        "placeholder.md"), ["AB-1"]), "ValueError")
    failures += report("flags", "a placeholder flag in a code span",
                       _error(check_flags, summary_file("## Remote flags\n- AB-1: `<flag>`\n",
                                                        "spanned.md"), ["AB-1"]), "ValueError")
    failures += report("flags", "a placeholder flag in emphasis or backslash escapes",
                       [_error(check_flags, summary_file(f"## Remote flags\n- AB-1: {value}\n",
                                                         "marked.md"), ["AB-1"])
                        for value in ("**<flag>**", "_<flag>_", "\\<flag\\>")],
                       ["ValueError"] * 3)
    failures += report("flags", "a flag name in a code span",
                       _error(check_flags, summary_file("## Remote flags\n- AB-1: `new_checkout`\n",
                                                        "named.md"), ["AB-1"]), "ok")
    failures += report("flags", "the notes check reads spaced keys",
                       _error(check_notes, summary_file(
                           "## Changes\n## Migrations\n## Known issues\n## Rollback\n"
                           "## Remote flags\n- AB-1: a\n- AB-2: none — a fix\n", "spaced.md"),
                           "AB-1, AB-2"), "ok")
    failures += report("flags", "any heading ends the section",
                       _error(check_flags, summary_file("## Remote flags\n# Other\n- AB-1: a\n",
                                                        "h1.md"), ["AB-1"]), "ValueError")
    failures += report("flags", "a key with an empty flag",
                       _error(check_flags, summary_file("## Remote flags\n- AB-1: \n",
                                                        "empty.md"), ["AB-1"]), "ValueError")
    failures += report("flags", "no section",
                       _error(check_flags, summary_file("## Changes\n- AB-1: x\n", "none.md"),
                              ["AB-1"]), "ValueError")
    return failures + sensitive_cases(directory)


def sensitive_cases(directory):
    """sensitive_paths against a real repository: one commit per change, tagged between."""
    failures = 0
    for pattern, expected in [("*.pem", [":(glob)**/*.pem", ":(glob)**/*.pem/**"]),
                              ("/keys/top.key", [":(glob)keys/top.key", ":(glob)keys/top.key/**"]),
                              ("auth", [":(glob)**/auth", ":(glob)**/auth/**"]),
                              ("src/auth/", [":(glob)src/auth/**"]),
                              ("docs/*", [":(glob)docs/*"]),
                              ("/*.pem", [":(glob)*.pem"]),
                              ("**/secrets", [":(glob)**/secrets", ":(glob)**/secrets/**"]),
                              ("apps/", [":(glob)**/apps/**"])]:
        failures += report("sensitive-paths", f"{pattern} as a pathspec", owners_pathspec(pattern),
                           expected)
    repo = os.path.join(directory, "repo")
    os.makedirs(os.path.join(repo, ".claude"))
    config = os.path.join(repo, ".claude", "project.json")
    with open(config, "w", encoding="utf-8") as handle:
        json.dump({"security_sensitive_paths":
                   "src/auth/ *.pem /keys/top.key docs/*.md vault *secret*"}, handle)

    def git(*arguments):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c",
                        "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-c",
                        "tag.gpgsign=false", *arguments],
                       cwd=repo, capture_output=True, check=True)

    def write(path, text="x"):
        full = os.path.join(repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(text)

    git("init", "-q", "--template=")
    write("src/auth/login.py")
    write("src/ui/view.py")
    git("add", "-A")
    git("commit", "-qm", "one")
    git("tag", "v1.0.0")
    write("src/ui/view.py", "y")
    git("commit", "-qam", "two")
    git("tag", "v1.1.0")
    git("mv", "src/auth/login.py", "src/ui/login.py")
    git("commit", "-qm", "three")
    git("tag", "v1.2.0")
    os.makedirs(os.path.join(repo, "src", "auth", "deep"))
    git("mv", "src/ui/login.py", "src/auth/deep/login.py")
    git("commit", "-qm", "four")
    git("tag", "v1.3.0")
    for path in ("keys/sub/a.pem", "keys/b.pem", "keys/top.key", "other/keys/top.key",
                 "docs/a.md", "docs/sub/b.md", "readme.txt", "lib/vault/key.txt",
                 "tab\tname.pem", "app/secrets/key.txt"):
        write(path)
    git("add", "-A")
    git("commit", "-qm", "five")
    for name, scope_range, expected in [
            ("an unchanged sensitive path", "v1.0.0..v1.1.0", []),
            ("a file moved out still matches", "v1.1.0..v1.2.0", ["src/auth/login.py"]),
            ("a directory pattern matches files at any depth below it", "v1.2.0..v1.3.0",
             ["src/auth/deep/login.py"]),
            ("slash-free, leading-slash, and anchored patterns, as CODEOWNERS reads them",
             "v1.3.0..HEAD", ["app/secrets/key.txt", "docs/a.md", "keys/b.pem", "keys/sub/a.pem",
                              "keys/top.key", "lib/vault/key.txt", "tab\tname.pem"]),
            ("a first release diffs from the empty tree", "v1.0.0", ["src/auth/login.py"]),
            ("a range that looks like an option", "--output=x", "ValueError"),
            ("a revision git does not know", "v9.0.0..HEAD", "ValueError")]:
        failures += report("sensitive-paths", name,
                           _result(sensitive_paths, config, scope_range), expected)
    for value in ("none", "<patterns>"):
        unset = os.path.join(directory, "unset.json")
        with open(unset, "w", encoding="utf-8") as handle:
            json.dump({"security_sensitive_paths": value}, handle)
        failures += report("sensitive-paths", f"{value} is not a pattern list",
                           _result(sensitive_paths, unset, "v1.0.0..HEAD"), "ValueError")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    version = commands.add_parser("version")
    version.add_argument("--new", required=True)
    version.add_argument("--last")
    listing = commands.add_parser("criteria")
    listing.add_argument("--config", required=True)
    note = commands.add_parser("note")
    note.add_argument("--summary", required=True)
    note.add_argument("--version", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--summary", required=True)
    verify.add_argument("--version", required=True)
    verify.add_argument("--require-pass", action="store_true")
    extract = commands.add_parser("nfrs")
    extract.add_argument("--key", required=True)
    settling = commands.add_parser("settle")
    settling.add_argument("--nfrs-file", required=True)
    settling.add_argument("--exceptions")
    settling.add_argument("--today", required=True)
    scope = commands.add_parser("scope")
    scope.add_argument("--summary", required=True)
    scope.add_argument("--range", required=True)
    scope.add_argument("--keys", required=True)
    commit = commands.add_parser("commit")
    commit.add_argument("--summary", required=True)
    commit.add_argument("--head", required=True)
    hashing = commands.add_parser("hash")
    hashing.add_argument("path")
    artifact = commands.add_parser("artifact")
    artifact.add_argument("--path", required=True)
    artifact.add_argument("--sha256-file", required=True)
    headings = commands.add_parser("notes-headings")
    headings.add_argument("--notes", required=True)
    headings.add_argument("--flag-keys")
    waived = commands.add_parser("excepted")
    waived.add_argument("--rule", required=True)
    waived.add_argument("--exceptions", required=True)
    waived.add_argument("--today", required=True)
    directory = commands.add_parser("release-dir")
    directory.add_argument("--value", required=True)
    named = commands.add_parser("disciplines")
    named.add_argument("--config", required=True)
    named.add_argument("--gate", choices=sorted(GATE_KEYS))
    for name in ("oldest-devices", "thresholds"):
        commands.add_parser(name).add_argument("--config", required=True)
    paths = commands.add_parser("sensitive-paths")
    paths.add_argument("--config", required=True)
    paths.add_argument("--range", required=True)
    commands.add_parser("error-budget")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        if args.command == "version":
            check_version(args.new, args.last)
            print("ok")
            return 0
        if args.command == "criteria":
            rows = criteria(sys.stdin.read(), declared_tiers(args.config))
            for row in rows:
                print("\t".join(row))
            return 0 if all(row[3] == "ok" for row in rows) else 1
        if args.command == "note":
            print(build_note(args.summary, args.version), end="")
            return 0
        if args.command == "nfrs":
            found, problems = nfrs(sys.stdin.read(), args.key)
            for line in found:
                print(line)
            for problem in problems:
                print(f"INVALID: {problem}", file=sys.stderr)
            return 1 if problems else 0
        if args.command == "settle":
            with open(args.nfrs_file, encoding="utf-8") as handle:
                in_scope = [line.strip() for line in handle if line.strip()]
            rows = settle(in_scope, sys.stdin.read(), exceptions(args.exceptions, args.today))
            for row in rows:
                print("\t".join(row))
            return 1 if any(row[1] == "fail" for row in rows) else 0
        if args.command == "disciplines":
            found = discipline_problems(args.config, args.gate)
            for problem in found:
                print(f"INVALID: {problem}", file=sys.stderr)
            if not found:
                print("ok")
            return 1 if found else 0
        listings = {"oldest-devices": lambda: oldest_devices(load_config(args.config)),
                    "thresholds": lambda: model_thresholds(load_config(args.config)),
                    "sensitive-paths": lambda: sensitive_paths(args.config, args.range)}
        if args.command in listings:
            for line in listings[args.command]():
                print(line)
            return 0
        if args.command == "error-budget":
            state, value = error_budget(sys.stdin.read())
            print(f"{state} {value}")
            return 0 if state == "ok" else 1
        if args.command == "hash":
            print(sha256(args.path))
            return 0
        checks = {"verify": lambda: verify_note(args.summary, args.version, sys.stdin.read(),
                                                args.require_pass),
                  "scope": lambda: check_scope(args.summary, args.range,
                                               [k for k in args.keys.split(",") if k]),
                  "commit": lambda: check_commit(args.summary, args.head),
                  "artifact": lambda: check_artifact(args.path, args.sha256_file),
                  "notes-headings": lambda: check_notes(args.notes, args.flag_keys),
                  "release-dir": lambda: check_release_dir(args.value),
                  "excepted": lambda: check_excepted(args.rule, args.exceptions, args.today)}
        if args.command in checks:
            try:
                checks[args.command]()
            except ValueError as error:
                print(f"MISMATCH: {error}", file=sys.stderr)
                return 1
            print("ok")
            return 0
    except (ValueError, OSError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1
    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
