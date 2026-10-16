#!/usr/bin/env python3
"""The release gates' deterministic checks, so no skill applies them by eye. Standard library only.

Called by skills/release-readiness/SKILL.md (Steps 1, 2, 4, 7) and skills/release/SKILL.md
(Steps 1 to 5).

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
    readiness_check.py notes-headings --notes PATH
    readiness_check.py release-dir --value VALUE
        each but hash prints `ok`, or INVALID/MISMATCH and exits 1
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
    match = SEMVER.match(new)
    if not match:
        raise ValueError(f"{new!r} is not MAJOR.MINOR.PATCH")
    if last:
        previous = SEMVER.match(last[1:]) if last.startswith("v") else None
        if not previous:
            raise ValueError(f"last tag {last!r} is not vMAJOR.MINOR.PATCH")
        if tuple(map(int, match.groups())) <= tuple(map(int, previous.groups())):
            raise ValueError(f"{new} is not greater than {last}")


def declared_tiers(config_path):
    with open(config_path, encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ValueError("project.json is not an object")
    value = config.get("verification_tiers", "")
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
    inside, fence = False, None
    item = re.compile(rf"^-\s+({kind}\d+):")
    stray = re.compile(rf"^\s*(?:[-*]|\d+\.)\s+({kind}\d+):")
    for line in description.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker and (fence is None or (marker.group(1)[0] == fence[0]
                                         and len(marker.group(1)) >= len(fence))):
            fence = None if fence else marker.group(1)
            continue
        if fence:
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
    if fence:
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
RELEASE_DIR = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._/-]*$")


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


REGISTER_COLUMNS = ("Rule", "Reason", "Risk", "Expiry", "Remediation")


def exceptions(path, today):
    """{Rule: Expiry} for every unexpired, complete row in a register table, in the format
    gates/exceptions.md defines: a row missing its reason, risk, or remediation records no
    exception, since nothing says why the waiver holds or how it ends."""
    if not path:
        return {}
    with open(path, encoding="utf-8") as handle:
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in handle if line.lstrip().startswith("|")]
    if not rows or tuple(rows[0][:len(REGISTER_COLUMNS)]) != REGISTER_COLUMNS:
        raise ValueError("the exceptions register's header is not "
                         + " | ".join(REGISTER_COLUMNS))
    rule, expiry = 0, REGISTER_COLUMNS.index("Expiry")
    return {row[rule]: row[expiry] for row in rows[1:]
            if len(row) >= len(REGISTER_COLUMNS)
            and all(row[n] and not re.fullmatch(r":?-+:?", row[n])
                    for n in range(len(REGISTER_COLUMNS)))
            and re.match(r"^\d{4}-\d{2}-\d{2}$", row[expiry]) and row[expiry] >= today}


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


def check_notes(notes_path):
    with open(notes_path, encoding="utf-8") as handle:
        lines = {line.rstrip() for line in handle}
    missing = [heading for heading in NOTES_HEADINGS if heading not in lines]
    if missing:
        raise ValueError(f"the notes lack {', '.join(missing)}")


def check_release_dir(value):
    if (not value or value == "none" or not RELEASE_DIR.match(value) or os.path.isabs(value)
            or os.path.normpath(value).split(os.sep)[0] in ("..", ".", ".git")):
        raise ValueError(f"release_dir {value!r} is not a relative path inside the repository "
                         "outside .git, starting with a letter, digit, or '_', and made only "
                         "of letters, digits, '.', '_', '-', and '/'")


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
                                  ("none", "none", "ValueError")]:
        failures += report("release-dir", name, _error(check_release_dir, value), expected)
    return failures


def _result(function, *arguments):
    try:
        return function(*arguments)
    except ValueError:
        return "ValueError"


def _error(function, *arguments):
    try:
        function(*arguments)
    except ValueError:
        return "ValueError"
    return "ok"


def report(kind, name, got, expected):
    if got == expected:
        print(f"ok   {kind}: {name}")
        return 0
    print(f"FAIL {kind}: {name} — expected {expected!r}, got {got!r}")
    return 1


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
    waived = commands.add_parser("excepted")
    waived.add_argument("--rule", required=True)
    waived.add_argument("--exceptions", required=True)
    waived.add_argument("--today", required=True)
    directory = commands.add_parser("release-dir")
    directory.add_argument("--value", required=True)
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
        if args.command == "hash":
            print(sha256(args.path))
            return 0
        checks = {"verify": lambda: verify_note(args.summary, args.version, sys.stdin.read(),
                                                args.require_pass),
                  "scope": lambda: check_scope(args.summary, args.range,
                                               [k for k in args.keys.split(",") if k]),
                  "commit": lambda: check_commit(args.summary, args.head),
                  "artifact": lambda: check_artifact(args.path, args.sha256_file),
                  "notes-headings": lambda: check_notes(args.notes),
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
