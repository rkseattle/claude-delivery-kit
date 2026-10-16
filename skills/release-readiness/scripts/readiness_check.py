#!/usr/bin/env python3
"""The release gates' deterministic checks, so no skill applies them by eye. Standard library only.

Called by skills/release-readiness/SKILL.md (Steps 2, 4, 7) and skills/release/SKILL.md (Step 1).

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
from lint_draft import VERIFY_TAG  # noqa: E402  the tag form write-tickets writes

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
# A criterion's tag ends its line, as lint_draft.py's AC pattern requires, so a tag quoted in
# the criterion's own wording is never read as its tag; a code span's closing backtick may follow.
BRACKET_TAG = re.compile(VERIFY_TAG + r"`?\s*$")
# Jira's Markdown conversion turns a tag written outside a code span into \verify: ... \.
# Its evidence may hold Jira's own escapes, such as \_ in a path; they are undone below.
ESCAPED_TAG = re.compile(r"\\verify:\s*([^@\\\s][^@\\]*?)\s*@\s*(\S.*?)\s*\\\s*$")
AC_LINE = re.compile(r"^-\s+(AC\d+):")
# A criterion in another list form, indented or marked with * or 1., is still a criterion.
STRAY_AC = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(AC\d+):")
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


def criteria(description, tiers):
    """[(ac, tier, evidence, status)] for the acceptance-criteria section, or no-criteria."""
    rows, inside, fence = [], False, None
    for line in description.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker and (fence is None or (marker.group(1)[0] == fence[0]
                                         and len(marker.group(1)) >= len(fence))):
            fence = None if fence else marker.group(1)
            continue
        if fence:
            continue
        if re.match(r"^#{1,6}\s", line):
            inside = re.match(r"^##\s+Acceptance criteria\s*$", line) is not None
            continue
        ac = AC_LINE.match(line) if inside else None
        if not ac:
            stray = STRAY_AC.match(line) if inside else None
            if stray:
                rows.append((stray.group(1), "-", "-", "not-in-the-ac-form"))
            continue
        # Jira may also escape a bracket tag's brackets as \[ and \].
        line = line.replace("\\[", "[").replace("\\]", "]")
        tag = BRACKET_TAG.search(line) or ESCAPED_TAG.search(line)
        if not tag:
            rows.append((ac.group(1), "-", "-", "no-tag"))
            continue
        tier = " ".join(tag.group(1).split())
        evidence = re.sub(r"\\(.)", r"\1", tag.group(2).strip())
        rows.append((ac.group(1), tier, evidence,
                     "ok" if tier.lower() in tiers else "undeclared-tier"))
    if fence:
        rows.append(("-", "-", "-", "unclosed-fence"))
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
        if args.command == "verify":
            try:
                verify_note(args.summary, args.version, sys.stdin.read(), args.require_pass)
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
