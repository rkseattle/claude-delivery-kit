#!/usr/bin/env python3
"""The scanners' git inputs and the verdicts the commit and push gates read from their SARIF
2.1.0 reports. Standard library only.

Called by gates/definition-of-done.md (steps 7 and 8) and gates/pre-push.md (steps 8, 9 and 11).

    sarif_gate.py patch --staged | --commits RANGE
        writes the secret scanner's input to stdout: the added lines of the staged diff, or
        of every commit in RANGE with its message indented; exit 2 if git fails
    sarif_gate.py renames BASE --staged | --head
        writes `git diff -z -M --name-status` from BASE to the index or HEAD, the --renames
        input of new-findings; exit 2 if git fails
    sarif_gate.py tree DIR --staged | --ref REF
        makes DIR a worktree holding exactly the index, added files tracked and deleted ones
        gone — or, before the first commit, an export of the index — or a worktree of REF;
        reports `worktree` or `export` on stderr; exit 2 if git fails or REF is empty
    sarif_gate.py secrets REPORT
        prints `clean`, or `findings N` and one `rule file:line` per finding — never the
        matched text; exit 0 only if clean
    sarif_gate.py new-findings STAGED BASE --staged-root DIR --base-root DIR [--renames FILE]
        prints `clean`, or `new N` and one `tool rule file +count` per key; exit 0 only if
        clean. FILE is `git diff -z -M --name-status <base> <staged>` output.
    sarif_gate.py new-findings STAGED --no-base --staged-root DIR
        the same with an empty base, where none exists
    sarif_gate.py --self-test     runs every case below; exit 0 only if each one matches

Exit 2 is an unusable report — missing, empty, not SARIF 2.1.0, with no runs, a run whose
results were not computed or whose invocation failed, a malformed entry, or a
security-severity that is not a number — never a verdict.
"""
import argparse
import collections
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

HIGH_SEVERITY = 7.0  # GitHub code scanning: High is 7.0-8.9, Critical 9.0 and above


def load(path):
    """The parsed report, or ValueError for anything that is not a usable SARIF 2.1.0 file."""
    try:
        with open(path, encoding="utf8") as handle:
            text = handle.read()
    except OSError as error:
        raise ValueError(f"cannot read {path}: {error.strerror}") from error
    if not text.strip():
        raise ValueError(f"{path} is empty")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} is not JSON: {error.msg}") from error
    if not isinstance(parsed, dict) or parsed.get("version") != "2.1.0":
        raise ValueError(f"{path} is not SARIF 2.1.0")
    runs = parsed.get("runs")
    if not isinstance(runs, list) or not runs or not all(isinstance(run, dict) for run in runs):
        raise ValueError(f"{path} has no runs")
    for run in runs:
        # An absent or null results means the tool computed none, not that it found none.
        if not isinstance(run.get("results"), list):
            raise ValueError(f"{path} has a run whose results were not computed")
        if not all(isinstance(result, dict) for result in run["results"]):
            raise ValueError(f"{path} has a result that is not an object")
        if any(isinstance(invocation, dict) and invocation.get("executionSuccessful") is False
               for invocation in run.get("invocations") or []):
            raise ValueError(f"{path} has a run whose invocation failed")
    return parsed


def results(sarif_report):
    """Every (run, result) pair. Suppressed results are included: a suppression added in the
    diff under review must not clear the finding it suppresses."""
    for run in sarif_report["runs"]:
        for result in run["results"]:
            # SARIF: pass, notApplicable and informational are no finding; review and open are
            # undecided, so they count.
            if result.get("kind", "fail") in ("fail", "review", "open"):
                yield run, result


def tool_name(run):
    return ((run.get("tool") or {}).get("driver") or {}).get("name") or ""


def rule_of(run, result):
    """(rule id, rule object or {}) by ruleId, rule.id, ruleIndex or rule.index, looking in
    the driver or the extension that rule.toolComponent names."""
    reference = result.get("rule") or {}
    tool = run.get("tool") or {}
    driver, extensions = tool.get("driver") or {}, list(tool.get("extensions") or [])
    named = reference.get("toolComponent")
    if named is None:
        components = [driver] + extensions
    else:
        # A rule in a component that cannot be found has no known rule, never the driver's.
        index = named.get("index")
        components = ([extensions[index]] if isinstance(index, int) and 0 <= index < len(extensions)
                      else [c for c in [driver] + extensions
                            if (named.get("guid") and c.get("guid") == named["guid"])
                            or (named.get("name") and c.get("name") == named["name"])][:1])
    index = result.get("ruleIndex", -1)
    if not isinstance(index, int) or index < 0:
        index = reference.get("index")
    rule = {}
    if components and isinstance(index, int) and index >= 0:
        rules = components[0].get("rules") or []
        rule = rules[index] if index < len(rules) else {}
    rule_id = result.get("ruleId") or reference.get("id") or rule.get("id") or ""
    if not rule and rule_id:
        # A hierarchical ruleId such as "X/1" names a sub-rule of the rule whose id is "X".
        wanted = [rule_id] + ([rule_id.split("/")[0]] if "/" in rule_id else [])
        rule = next((candidate for want in wanted for component in components
                     for candidate in component.get("rules") or []
                     if candidate.get("id") == want), {})
    return rule_id, rule


def is_high(run, result):
    """security-severity of at least 7.0 on the rule, else on the result; with neither, a
    level of error, defaulting through the rule's defaultConfiguration to warning."""
    _, rule = rule_of(run, result)
    for properties in ((rule.get("properties") or {}), (result.get("properties") or {})):
        if "security-severity" in properties:
            value = properties["security-severity"]
            try:
                severity = None if isinstance(value, bool) else float(value)
            except (TypeError, ValueError):
                severity = None
            if severity is None or not math.isfinite(severity):
                raise ValueError(f"security-severity {value!r} is not a number")
            return severity >= HIGH_SEVERITY
    level = result.get("level") or (rule.get("defaultConfiguration") or {}).get("level") or "warning"
    return level == "error"


def location_of(run, result, root):
    """The first location's file relative to the scanned root, and its start line."""
    locations = result.get("locations") or [{}]
    physical = (locations[0] or {}).get("physicalLocation") or {}
    artifact = physical.get("artifactLocation") or {}
    uri = artifact.get("uri") or ""
    base_id = artifact.get("uriBaseId")
    seen = set()
    while base_id and base_id not in seen:
        seen.add(base_id)
        base = (run.get("originalUriBaseIds") or {}).get(base_id) or {}
        uri = urllib.parse.urljoin(base.get("uri") or "", uri) if base.get("uri") else uri
        base_id = base.get("uriBaseId")
    parsed = urllib.parse.urlparse(uri)
    path = urllib.parse.unquote(parsed.path if parsed.scheme == "file" else uri)
    if os.path.isabs(path) and root:
        path = os.path.relpath(os.path.realpath(path), os.path.realpath(root))
    line = ((physical.get("region") or {}).get("startLine")) or 0
    return os.path.normpath(path) if path else "", line


def secret_findings(sarif_report):
    """`rule file:line` per result; the matched text never leaves the report."""
    found = []
    for run, result in results(sarif_report):
        rule_id, _ = rule_of(run, result)
        path, line = location_of(run, result, None)
        found.append(f"{rule_id} {path}:{line}")
    return found


def fingerprint(result):
    """The tool's stable identity for a finding, as GitHub code scanning matches alerts across
    commits: fingerprints, else partialFingerprints, or None when the tool gives neither."""
    for field in ("fingerprints", "partialFingerprints"):
        values = result.get(field)
        if isinstance(values, dict) and values:
            return json.dumps(sorted(values.items()))
    return None


def high_counts(sarif_report, root, renames=None, renamed=frozenset()):
    """High or Critical results counted by identity — the fingerprint where the tool gives
    one, else tool, rule and file — with the file each identity was found in. A file in
    `renamed` is matched by path: a fingerprint may hash the path, which the rename changed."""
    counts, files = collections.Counter(), {}
    for run, result in results(sarif_report):
        if is_high(run, result):
            path, _ = location_of(run, result, root)
            path = (renames or {}).get(path, path)
            mark = None if path in renamed else fingerprint(result)
            identity = (tool_name(run), rule_of(run, result)[0], mark or path, mark is not None)
            counts[identity] += 1
            files[identity] = path
    return counts, files


def new_findings(staged, base, staged_root, base_root, renames=None):
    """(tool, rule, file) with how many High or Critical findings it gained over the base. A
    fingerprinted finding is new unless the base has the same fingerprint, so one fixed and
    another added in the same file is still caught."""
    renamed = frozenset((renames or {}).values())
    before = high_counts(base, base_root, renames, renamed)[0] if base else collections.Counter()
    after, files = high_counts(staged, staged_root, renamed=renamed)
    new = collections.Counter()
    for identity, count in after.items():
        if count > before[identity]:
            new[(identity[0], identity[1], files[identity])] += count - before[identity]
    return dict(new)


def parse_renames(text):
    """{base path: staged path} from `git diff -z -M --name-status`, whose NUL-separated
    fields carry paths unquoted: `R<score>` old new, every other status one path."""
    fields, renames, position = text.split("\0"), {}, 0
    while position < len(fields) and fields[position]:
        status = fields[position]
        width = 3 if status.startswith(("R", "C")) else 2
        if position + width > len(fields) or not all(fields[position + 1:position + width]):
            raise ValueError("the renames file ends partway through an entry")
        if status.startswith(("R", "C")):
            if status.startswith("R"):
                renames[os.path.normpath(fields[position + 1])] = os.path.normpath(fields[position + 2])
            position += 3
        else:
            position += 2
    return renames


# Every diff a gate reads ignores the user's diff configuration: a relative diff from a
# subdirectory would drop changes outside it, and textconv would decrypt git-crypt files.
GIT_DIFF = ["--no-color", "--no-ext-diff", "--no-textconv", "--no-relative", "--src-prefix=a/",
            "--dst-prefix=b/"]
HUNK_HEADER = re.compile(rb"^(@@ [^@]* @@)")
GIT_ENVIRONMENT = None  # the self-test's isolated environment; None is the caller's


def git(*arguments, cwd=None):
    """git's stdout as bytes, or ValueError naming the subcommand that failed."""
    completed = subprocess.run(["git", *arguments], cwd=cwd, capture_output=True, check=False,
                               env=GIT_ENVIRONMENT)
    if completed.returncode != 0:
        message = completed.stderr.decode("utf8", "replace").strip().splitlines()
        command = next((a for a in arguments if not a.startswith("-")), arguments[0])
        raise ValueError(f"git {command} failed: {message[-1] if message else completed.returncode}")
    return completed.stdout


def added_lines(patch):
    """Only what the patch adds: removed lines and their --- headers go, and a hunk header
    loses the context line git copies after it. A removed line is a secret leaving, and
    context is code this change did not write."""
    kept = []
    for line in patch.split(b"\n"):
        if line.startswith(b"-"):
            continue
        header = HUNK_HEADER.match(line)
        kept.append(header.group(1) if header else line)
    return b"\n".join(kept)


def staged_patch(cwd=None):
    return added_lines(git("diff", "--cached", "-U0", *GIT_DIFF, cwd=cwd))


def commits_patch(revision_range, cwd=None):
    """Every commit's message and patch, not the net diff: a secret added in one commit and
    deleted in a later one is still pushed. The indent keeps a message line that starts
    with `-` from reading as a removal."""
    return added_lines(git("log", "-p", "-U0", *GIT_DIFF, "--diff-merges=first-parent",
                           "--format=%w(0,4,4)%B", revision_range, cwd=cwd))


def rename_status(base, staged=True, cwd=None):
    target = ["--cached", base] if staged else [base, "HEAD"]
    return git("diff", "-z", "-M", "--name-status", *GIT_DIFF, *target, cwd=cwd)


def make_tree(directory, ref=None, cwd=None):
    """With a ref, DIR is a worktree of it. Without, DIR is a worktree of HEAD given the
    index's tree with read-tree, so its files and index are exactly what the commit records
    — nothing unstaged — and no diff configuration is involved; before the first commit it
    is an export of the index instead. Returns `worktree` or `export`."""
    if ref is not None:
        if not ref:
            raise ValueError("an empty ref names no tree")  # an unset $merge_base, say
        git("worktree", "add", "--detach", directory, ref, cwd=cwd)
        return "worktree"
    try:
        git("rev-parse", "--verify", "--quiet", "HEAD", cwd=cwd)
    except ValueError:
        git("checkout-index", "--all", f"--prefix={os.path.join(directory, '')}", cwd=cwd)
        return "export"
    tree = git("write-tree", cwd=cwd).decode().strip()
    git("worktree", "add", "--detach", directory, "HEAD", cwd=cwd)
    try:
        git("read-tree", "-u", "--reset", tree, cwd=directory)
    except ValueError:
        try:
            git("worktree", "remove", "--force", directory, cwd=cwd)
        except ValueError:
            pass  # the read-tree failure is the one to report
        raise
    return "worktree"


# Fixtures. Each case is one way a finding could pass when it should block, or block when it
# should pass.
def sarif(*runs):
    return {"version": "2.1.0", "runs": list(runs)}


def run(results_list, rules=None, extensions=None, name="analyzer", bases=None):
    tool = {"driver": {"name": name, "rules": rules or []}}
    if extensions is not None:
        tool["extensions"] = extensions
    entry = {"tool": tool, "results": results_list}
    if bases is not None:
        entry["originalUriBaseIds"] = bases
    return entry


def finding(uri, rule_id="r1", line=1, **extra):
    result = {"ruleId": rule_id, "locations": [{"physicalLocation": {
        "artifactLocation": {"uri": uri}, "region": {"startLine": line}}}]}
    result.update(extra)
    return result


RENAMES = ("M\0src/c.py\0R100\0src/a.py\0src/moved.py\0C075\0src/c.py\0src/copy.py\0"
           "A\0new.py\0R090\0caf\u00e9.py\0src/b\u00e9.py\0")
HIGH_RULE = {"id": "r1", "properties": {"security-severity": "8.8"}}
LOW_RULE = {"id": "r1", "properties": {"security-severity": "6.9"}}
DEBT = sarif(run([finding("src/a.py")], [HIGH_RULE]))

NEW_FINDINGS_CASES = [
    ("debt already on the base", DEBT, DEBT, {}),
    ("a High in a new file", sarif(run([finding("src/a.py"), finding("src/b.py")], [HIGH_RULE])),
     DEBT, {("analyzer", "r1", "src/b.py"): 1}),
    ("a second High in a file that already had one",
     sarif(run([finding("src/a.py"), finding("src/a.py", line=9)], [HIGH_RULE])),
     DEBT, {("analyzer", "r1", "src/a.py"): 1}),
    ("a suppression added in the diff",
     sarif(run([finding("src/a.py"), finding("src/a.py", line=9,
                                             suppressions=[{"kind": "inSource", "status": "accepted"}])],
               [HIGH_RULE])),
     DEBT, {("analyzer", "r1", "src/a.py"): 1}),
    ("a severity below 7.0", sarif(run([finding("src/b.py")], [LOW_RULE])), None, {}),
    ("severity on the rule a ruleIndex names",
     sarif(run([{"ruleIndex": 0, "locations": finding("src/b.py")["locations"]}], [HIGH_RULE])),
     None, {("analyzer", "r1", "src/b.py"): 1}),
    ("severity on an extension's rule",
     sarif(run([{"rule": {"id": "q1", "index": 0, "toolComponent": {"index": 0}},
                 "locations": finding("src/b.py")["locations"]}],
               extensions=[{"name": "pack", "rules": [{"id": "q1", "properties": {"security-severity": 9.1}}]}])),
     None, {("analyzer", "q1", "src/b.py"): 1}),
    ("severity on the result only",
     sarif(run([finding("src/b.py", properties={"security-severity": "7.0"})])),
     None, {("analyzer", "r1", "src/b.py"): 1}),
    ("no severity, level error", sarif(run([finding("src/b.py", level="error")])),
     None, {("analyzer", "r1", "src/b.py"): 1}),
    ("no severity, level error from the rule's default",
     sarif(run([finding("src/b.py")], [{"id": "r1", "defaultConfiguration": {"level": "error"}}])),
     None, {("analyzer", "r1", "src/b.py"): 1}),
    ("no severity and no level", sarif(run([finding("src/b.py")])), None, {}),
    ("rule severity below 7.0 outranks a result's level error",
     sarif(run([finding("src/b.py", level="error")], [LOW_RULE])), None, {}),
    ("rule severity outranks the result's own",
     sarif(run([finding("src/b.py", properties={"security-severity": "9.0"})], [LOW_RULE])), None, {}),
    ("a toolComponent index out of range never borrows the driver's rule",
     sarif(run([{"ruleIndex": 0, "rule": {"index": 0, "toolComponent": {"index": 5}},
                 "locations": finding("src/b.py")["locations"]}], [HIGH_RULE], extensions=[])),
     None, {}),
    ("a toolComponent named rather than indexed",
     sarif(run([{"rule": {"index": 0, "toolComponent": {"name": "pack"}},
                 "locations": finding("src/b.py")["locations"]}], [LOW_RULE],
               extensions=[{"name": "pack", "rules": [{"id": "q1", "properties": {"security-severity": 9.1}}]}])),
     None, {("analyzer", "q1", "src/b.py"): 1}),
    ("severity on the parent of a hierarchical ruleId",
     sarif(run([finding("src/b.py", "r1/sub")], [HIGH_RULE])), None, {("analyzer", "r1/sub", "src/b.py"): 1}),
    ("a toolComponent found by guid",
     sarif(run([{"rule": {"index": 0, "toolComponent": {"guid": "g-1"}},
                 "locations": finding("src/b.py")["locations"]}], [LOW_RULE],
               extensions=[{"guid": "g-1", "rules": [{"id": "q1", "properties": {"security-severity": 9.1}}]}])),
     None, {("analyzer", "q1", "src/b.py"): 1}),
    ("a ruleIndex past the rules list falls back to the id",
     sarif(run([finding("src/b.py", ruleIndex=4)], [HIGH_RULE])), None, {("analyzer", "r1", "src/b.py"): 1}),
    ("a ruleIndex of -1 defers to rule.index",
     sarif(run([{"ruleIndex": -1, "rule": {"index": 0}, "locations": finding("src/b.py")["locations"]}],
               [HIGH_RULE])), None, {("analyzer", "r1", "src/b.py"): 1}),
    ("a result whose kind is pass", sarif(run([finding("src/b.py", kind="pass")], [HIGH_RULE])), None, {}),
    ("one High fixed and another added in the same file",
     sarif(run([finding("src/a.py", line=9, partialFingerprints={"primaryLocationLineHash": "new:1"})], [HIGH_RULE])),
     sarif(run([finding("src/a.py", partialFingerprints={"primaryLocationLineHash": "old:1"})], [HIGH_RULE])),
     {("analyzer", "r1", "src/a.py"): 1}),
    ("a fingerprinted finding that moved lines and files",
     sarif(run([finding("src/z.py", line=40, partialFingerprints={"primaryLocationLineHash": "old:1"})], [HIGH_RULE])),
     sarif(run([finding("src/a.py", partialFingerprints={"primaryLocationLineHash": "old:1"})], [HIGH_RULE])), {}),
    ("a fingerprint that hashes the path, across a rename",
     sarif(run([finding("src/moved.py", partialFingerprints={"matchBasedId/v1": "moved:h"})], [HIGH_RULE])),
     sarif(run([finding("src/a.py", partialFingerprints={"matchBasedId/v1": "a:h"})], [HIGH_RULE])), {}),
    ("an undecided result whose kind is review",
     sarif(run([finding("src/b.py", kind="review")], [HIGH_RULE])), None, {("analyzer", "r1", "src/b.py"): 1}),
    ("the same key from a different tool",
     sarif(run([finding("src/a.py")], [HIGH_RULE]), run([finding("src/a.py")], [HIGH_RULE], name="other")),
     DEBT, {("other", "r1", "src/a.py"): 1}),
]


def self_test():
    failures = 0
    case_renames = parse_renames("R100\0src/a.py\0src/moved.py\0")
    for name, staged, base, expected in NEW_FINDINGS_CASES:
        got = new_findings(staged, base, "/s", "/b", case_renames if "rename" in name else None)
        failures += report("new-findings", name, got, expected)
    absolute = new_findings(sarif(run([finding("file:///s/src/a.py")], [HIGH_RULE])),
                            sarif(run([finding("file:///b/src/a.py")], [HIGH_RULE])), "/s", "/b")
    failures += report("new-findings", "absolute URIs under different roots", absolute, {})
    based = sarif(run([finding("src/a.py")], [HIGH_RULE], bases={"SRC": {"uri": "file:///s/"}}))
    based["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uriBaseId"] = "SRC"
    failures += report("new-findings", "a uriBaseId resolved through originalUriBaseIds",
                       new_findings(based, DEBT, "/s", "/b"), {})
    renamed = sarif(run([finding("src/moved.py")], [HIGH_RULE]))
    failures += report("new-findings", "a renamed file carrying base debt",
                       new_findings(renamed, DEBT, "/s", "/b", parse_renames(RENAMES)), {})
    failures += report("renames", "other statuses and an unquoted non-ASCII path",
                       parse_renames(RENAMES), {"src/a.py": "src/moved.py", "caf\u00e9.py": "src/b\u00e9.py"})
    cyclic = sarif(run([finding("src/a.py")], [HIGH_RULE], bases={"A": {"uri": "x/", "uriBaseId": "B"},
                                                                     "B": {"uriBaseId": "A"}}))
    cyclic["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uriBaseId"] = "A"
    failures += report("new-findings", "a uriBaseId cycle ends", new_findings(cyclic, None, "/s", None),
                       {("analyzer", "r1", "x/src/a.py"): 1})
    with tempfile.TemporaryDirectory() as real:
        link = real + ".link"
        os.symlink(real, link)
        try:
            through_link = new_findings(sarif(run([finding("file://" + os.path.realpath(real) + "/src/a.py")], [HIGH_RULE])),
                                        DEBT, link, "/b")
        finally:
            os.unlink(link)
    failures += report("new-findings", "a root reached through a symlink", through_link, {})
    encoded = new_findings(sarif(run([finding("file:///s/src/my%20file.py")], [HIGH_RULE])),
                           sarif(run([finding("src/my file.py")], [HIGH_RULE])), "/s", "/b")
    failures += report("new-findings", "a percent-encoded file URI", encoded, {})
    failures += report("new-findings", "no base", new_findings(DEBT, None, "/s", None),
                       {("analyzer", "r1", "src/a.py"): 1})
    try:
        new_findings(sarif(run([finding("src/a.py", properties={"security-severity": "high"})])), None, "/s", None)
        failures += report("new-findings", "a non-numeric severity", "verdict", "ValueError")
    except ValueError:
        failures += report("new-findings", "a non-numeric severity", "ValueError", "ValueError")
    for value in ("nan", True):
        try:
            new_findings(sarif(run([finding("src/a.py", properties={"security-severity": value})])), None, "/s", None)
            failures += report("new-findings", f"a severity of {value!r}", "verdict", "ValueError")
        except ValueError:
            failures += report("new-findings", f"a severity of {value!r}", "ValueError", "ValueError")
    failures += report("secrets", "a clean report", secret_findings(sarif(run([]))), [])
    failures += report("secrets", "a suppressed secret still counts",
                       secret_findings(sarif(run([finding("cfg.env", "aws-key", 3,
                                                          suppressions=[{"kind": "inSource"}],
                                                          message={"text": "AKIA..."})]))),
                       ["aws-key cfg.env:3"])
    failures += cli_cases()
    failures += git_cases()
    return 1 if failures else 0


def git_cases():
    """Each case runs against a scratch repository with no user or system git config."""
    failures = 0
    global GIT_ENVIRONMENT
    # An inherited GIT_DIR, GIT_INDEX_FILE or GIT_CONFIG_PARAMETERS would aim the fixture at
    # another repository or configuration, so none survives.
    GIT_ENVIRONMENT = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    GIT_ENVIRONMENT.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_AUTHOR_NAME="t",
                           GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    try:
        with tempfile.TemporaryDirectory() as scratch:
            repo = os.path.join(scratch, "repo")
            def write(path, content, mode="w"):
                with open(os.path.join(repo, path), mode) as handle:
                    handle.write(content)
            git("init", "--quiet", repo)
            write("kept.py", "a = 1\nb = 2\nc = 3\n")
            git("add", "kept.py", cwd=repo)
            failures += report("tree", "an export before the first commit", (
                make_tree(os.path.join(scratch, "unborn"), cwd=repo),
                sorted(os.listdir(os.path.join(scratch, "unborn")))), ("export", ["kept.py"]))
            write("gone.txt", "old\n")
            write("blob.bin", b"\x00\x01", "wb")
            write(".gitattributes", "*.enc diff=reveal\n")
            write("secret.enc", "ciphertext\n")
            git("config", "diff.reveal.textconv", "sed s/ciphertext/PLAINTEXT/", cwd=repo)
            # Diff settings a user may have, none of which may change what a gate reads.
            for key, value in (("diff.relative", "true"), ("color.diff", "always"),
                               ("color.ui", "always"), ("diff.noprefix", "true")):
                git("config", key, value, cwd=repo)
            os.mkdir(os.path.join(repo, "sub"))
            git("add", ".", cwd=repo)
            git("commit", "--quiet", "-m", "base", cwd=repo)
            write("kept.py", "a = 1\nb = 2\nc = 3\nd = 4\n")
            write("new.py", "token = 'added'\n")
            write("blob.bin", b"\x00\x01\x02", "wb")
            write("secret.enc", "ciphertext2\n")
            git("rm", "--quiet", "gone.txt", cwd=repo)
            git("add", ".", cwd=repo)
            write("kept.py", "unstaged = True\n")
            failures += report("patch", "the textconv driver is live in this fixture",
                               b"PLAINTEXT" in git("diff", "--cached", "--no-color", cwd=repo), True)
            patch = staged_patch(cwd=os.path.join(repo, "sub"))
            failures += report("patch", "added lines in, removed and context out", (
                b"+d = 4" in patch, b"+token = 'added'" in patch, b"old" in patch,
                b"c = 3" in patch, b"unstaged" in patch), (True, True, False, False, False))
            failures += report("patch", "textconv never runs", b"PLAINTEXT" in patch, False)
            failures += report("patch", "paths keep their prefix under diff.noprefix",
                               b"+++ b/new.py" in patch, True)
            failures += report("renames", "the staged deletion from a subdirectory",
                               b"gone.txt" in rename_status("HEAD", cwd=os.path.join(repo, "sub")), True)
            tree = os.path.join(scratch, "staged")
            mode = make_tree(tree, cwd=repo)
            listed = git("ls-files", cwd=tree).decode().split()
            with open(os.path.join(tree, "kept.py")) as handle:
                kept = handle.read()
            with open(os.path.join(tree, "blob.bin"), "rb") as handle:
                blob = handle.read()
            failures += report("tree", "the index, tracked, without unstaged edits", (
                mode, "new.py" in listed, "gone.txt" in listed, kept.endswith("d = 4\n"),
                blob, git("diff", "--name-only", cwd=tree) + git("ls-files", "--others", cwd=tree),
                git("diff", "--cached", "--binary", "HEAD", cwd=tree)
                == git("diff", "--cached", "--binary", "HEAD", cwd=repo)),
                ("worktree", True, False, True, b"\x00\x01\x02", b"", True))
            try:
                make_tree(tree, cwd=repo)
                failures += report("tree", "a directory already in use", "made", "ValueError")
            except ValueError:
                failures += report("tree", "a directory already in use", "ValueError", "ValueError")
            git("worktree", "remove", "--force", tree, cwd=repo)
            git("checkout", "--quiet", "--", "kept.py", cwd=repo)
            git("commit", "--quiet", "-m", "add\n\n- leaked: AKIAADDED", cwd=repo)
            write("new.py", "token = 'clean'\n")
            git("commit", "--quiet", "-am", "scrub", cwd=repo)
            failures += report("renames", "from a base to HEAD",
                               b"gone.txt" in rename_status("HEAD~2", staged=False, cwd=repo), True)
            git("checkout", "--quiet", "-b", "side", "HEAD~1", cwd=repo)
            write("side.py", "side = 1\n")
            git("add", "side.py", cwd=repo)
            git("commit", "--quiet", "-m", "side", cwd=repo)
            git("checkout", "--quiet", "-", cwd=repo)
            git("merge", "--quiet", "--no-commit", "side", cwd=repo)
            write("side.py", "side = 1\nfrom_merge = 'only in the merge'\n")
            git("commit", "--quiet", "-am", "merge", cwd=repo)
            failures += report("patch", "content only a merge commit adds",
                               b"only in the merge" in commits_patch("HEAD~1..HEAD", cwd=repo), True)
            git("reset", "--quiet", "--hard", "HEAD~1", cwd=repo)
            pushed = commits_patch("HEAD~2..HEAD", cwd=repo)
            failures += report("patch", "a secret deleted in a later commit is still pushed",
                               b"token = 'added'" in pushed, True)
            failures += report("patch", "a message line starting with - survives",
                               b"    - leaked: AKIAADDED" in pushed, True)
            try:
                commits_patch("no-such-ref..HEAD", cwd=repo)
                failures += report("patch", "git failing", "patch", "ValueError")
            except ValueError:
                failures += report("patch", "git failing", "ValueError", "ValueError")
            at_ref = os.path.join(scratch, "at-ref")
            failures += report("tree", "a worktree of a ref", (
                make_tree(at_ref, "HEAD~1", cwd=repo),
                git("rev-parse", "HEAD", cwd=at_ref) == git("rev-parse", "HEAD~1", cwd=repo)),
                ("worktree", True))
            git("worktree", "remove", "--force", at_ref, cwd=repo)
            run_cli = lambda *arguments: subprocess.run(
                [sys.executable, os.path.abspath(__file__), *arguments], capture_output=True,
                cwd=repo, check=False, env=GIT_ENVIRONMENT)
            failures += report("cli", "tree with an empty ref", run_cli("tree", at_ref, "--ref", "").returncode, 2)
            listed = run_cli("renames", "HEAD~2", "--head")
            failures += report("cli", "renames --head", (listed.returncode, b"gone.txt" in listed.stdout), (0, True))
            listed = run_cli("renames", "HEAD", "--staged")
            failures += report("cli", "renames --staged with nothing staged", (listed.returncode, listed.stdout), (0, b""))
            produced = run_cli("patch", "--commits", "HEAD~1..HEAD")
            failures += report("cli", "patch --commits", (produced.returncode, b"token = 'clean'" in produced.stdout), (0, True))
            built = run_cli("tree", at_ref, "--staged")
            failures += report("cli", "tree --staged", (built.returncode, built.stdout, built.stderr.strip()), (0, b"", b"worktree"))
            git("worktree", "remove", "--force", at_ref, cwd=repo)
            outside = os.path.join(scratch, "outside")
            os.mkdir(outside)
            for name, arguments in (("patch outside a repository", ["patch", "--staged"]),
                                    ("tree outside a repository", ["tree", "t", "--staged"]),
                                    ("tree of a missing ref", ["tree", "t", "--ref", "nope"]),
                                    ("renames from a missing base", ["renames", "nope", "--head"])):
                completed = subprocess.run(
                    [sys.executable, os.path.abspath(__file__), *arguments], capture_output=True,
                    cwd=outside if arguments[-1] == "--staged" or arguments[0] == "patch" else repo, check=False,
                    env=dict(GIT_ENVIRONMENT, GIT_CEILING_DIRECTORIES=scratch))
                failures += report("cli", name, completed.returncode, 2)
    finally:
        GIT_ENVIRONMENT = None
    return failures


def cli_cases():
    failures = 0
    with tempfile.TemporaryDirectory() as scratch:
        def write(name, content):
            path = os.path.join(scratch, name)
            with open(path, "w", encoding="utf8") as handle:
                handle.write(content if isinstance(content, str) else json.dumps(content))
            return path
        debt, staged = write("debt.sarif", DEBT), write("staged.sarif", NEW_FINDINGS_CASES[1][1])
        cases = [
            ("a missing report", ["secrets", os.path.join(scratch, "absent")], 2),
            ("an empty report", ["secrets", write("empty", "")], 2),
            ("a report that is not JSON", ["secrets", write("text", "Scan complete")], 2),
            ("a report of another SARIF version", ["secrets", write("v1", {"version": "1.0.0", "runs": []})], 2),
            ("a report without runs[]", ["secrets", write("noruns", {"version": "2.1.0"})], 2),
            ("a report with no runs", ["secrets", write("zeroruns", sarif())], 2),
            ("a run whose results were not computed",
             ["secrets", write("noresults", {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "x"}}}]})], 2),
            ("a run whose results are not a list",
             ["secrets", write("objresults", {"version": "2.1.0", "runs": [{"results": {}}]})], 2),
            ("a run whose invocation failed",
             ["secrets", write("failed", {"version": "2.1.0", "runs": [
                 {"results": [], "invocations": [{"executionSuccessful": False}]}]})], 2),
            ("a result that is not an object",
             ["secrets", write("junk", {"version": "2.1.0", "runs": [{"results": ["junk", 5]}]})], 2),
            ("locations that are an object",
             ["secrets", write("locobj", sarif(run([{"ruleId": "r", "locations": {"a": 1}}])))], 2),
            ("a truncated renames file",
             ["new-findings", debt, debt, "--staged-root", scratch, "--base-root", scratch,
              "--renames", write("cut", "R100\0src/a.py\0")], 2),
            ("a malformed entry", ["secrets", write("tool", {"version": "2.1.0", "runs": [
                {"tool": "x", "results": [{"ruleId": "r"}]}]})], 2),
            ("a non-numeric severity",
             ["new-findings", write("word", sarif(run([finding("a", properties={"security-severity": "high"})]))),
              "--no-base", "--staged-root", scratch], 2),
            ("a base and --no-base together", ["new-findings", debt, debt, "--no-base", "--staged-root", scratch], 2),
            ("neither a base nor --no-base", ["new-findings", debt, "--staged-root", scratch], 2),
            ("a rename read from a file",
             ["new-findings", write("moved", sarif(run([finding("src/moved.py")], [HIGH_RULE]))), debt,
              "--staged-root", scratch, "--base-root", scratch, "--renames", write("renames", RENAMES)], 0),
            ("a clean secret scan", ["secrets", write("clean", sarif(run([])))], 0),
            ("a secret found", ["secrets", debt], 1),
            ("debt only", ["new-findings", debt, debt, "--staged-root", scratch, "--base-root", scratch], 0),
            ("a new High", ["new-findings", staged, debt, "--staged-root", scratch, "--base-root", scratch], 1),
            ("no base", ["new-findings", debt, "--no-base", "--staged-root", scratch], 1),
            ("a base report that is missing",
             ["new-findings", debt, os.path.join(scratch, "absent"), "--staged-root", scratch, "--base-root", scratch], 2),
        ]
        for name, arguments, expected_exit in cases:
            completed = subprocess.run([sys.executable, os.path.abspath(__file__), *arguments],
                                       capture_output=True, text=True, check=False)
            failures += report("cli", name, completed.returncode, expected_exit)
        leaked = subprocess.run([sys.executable, os.path.abspath(__file__), "secrets",
                                 write("leak", sarif(run([finding("a", message={"text": "s3cr3t"},
                                                                  partialFingerprints={"x": "s3cr3t"})])))],
                                capture_output=True, text=True, check=False)
        failures += report("cli", "the matched text is never printed", "s3cr3t" in leaked.stdout + leaked.stderr, False)
    return failures


def report(check, name, got, expected):
    if got == expected:
        print(f"ok   {check}: {name}")
        return 0
    print(f"FAIL {check}: {name} — expected {expected!r}, got {got!r}")
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    secrets = commands.add_parser("secrets")
    secrets.add_argument("report")
    compare = commands.add_parser("new-findings")
    compare.add_argument("staged")
    compare.add_argument("base", nargs="?")
    compare.add_argument("--staged-root", required=True)
    compare.add_argument("--base-root")
    compare.add_argument("--renames")
    compare.add_argument("--no-base", action="store_true")
    produce = commands.add_parser("patch")
    source = produce.add_mutually_exclusive_group(required=True)
    source.add_argument("--staged", action="store_true")
    source.add_argument("--commits", metavar="RANGE")
    moved = commands.add_parser("renames")
    moved.add_argument("base")
    side = moved.add_mutually_exclusive_group(required=True)
    side.add_argument("--staged", action="store_true")
    side.add_argument("--head", action="store_true")
    materialize = commands.add_parser("tree")
    materialize.add_argument("directory")
    content = materialize.add_mutually_exclusive_group(required=True)
    content.add_argument("--staged", action="store_true")
    content.add_argument("--ref")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        if args.command == "patch":
            sys.stdout.buffer.write(staged_patch() if args.staged else commits_patch(args.commits))
            return 0
        if args.command == "renames":
            sys.stdout.buffer.write(rename_status(args.base, staged=args.staged))
            return 0
        if args.command == "tree":
            print(make_tree(args.directory, args.ref), file=sys.stderr)
            return 0
        if args.command == "secrets":
            found = secret_findings(load(args.report))
            print(f"findings {len(found)}" if found else "clean")
            for entry in found:
                print(entry)
            return 1 if found else 0
        if args.command == "new-findings":
            if args.no_base == bool(args.base) or (args.base and not args.base_root):
                parser.error("give BASE with --base-root, or --no-base")
            renames = {}
            if args.renames:
                with open(args.renames, encoding="utf8", errors="surrogateescape") as handle:
                    renames = parse_renames(handle.read())
            base = None if args.no_base else load(args.base)
            new = new_findings(load(args.staged), base, args.staged_root, args.base_root, renames)
            print(f"new {sum(new.values())}" if new else "clean")
            for (tool, rule_id, path), rise in sorted(new.items()):
                print(f"{tool} {rule_id} {path} +{rise}")
            return 1 if new else 0
    except (ValueError, OSError, AttributeError, TypeError, IndexError, KeyError) as error:
        # A wrong-shaped entry in a parseable report is an unusable report, not a finding.
        print(f"UNUSABLE: {error}", file=sys.stderr)
        return 2
    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
