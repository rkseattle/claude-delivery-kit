#!/usr/bin/env python3
"""Lint a write-tickets draft. Standard library only.

    lint_draft.py DRAFT.md [--repo ROOT]   exit 0 clean, 1 errors, 2 unparseable
    lint_draft.py DRAFT.md --readback ID FETCHED.md
                                           exit 0 if Jira kept every line of ticket ID, 1 if not
    lint_draft.py --self-test              runs the fixtures; exit 0 only if every count matches

Checks what a script can settle. Whether a ticket is plannable is ticket-adversary's call.
"""
import argparse
import contextlib
import difflib
import io
import os
import re
import shutil
import sys
import tempfile

from jira_roundtrip import PROBES, roundtrip

SUMMARY_MAX = 100

# plan-work Step 1 states the handoff limit in prose. Read it from there rather than
# copying the number: the rubric refuses to restate plan-work's limits, and so does this.
PLAN_WORK_SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               os.pardir, os.pardir, "plan-work", "SKILL.md")
HANDOFF_LIMIT_SENTENCE = re.compile(r"working limit for a single\s+handoff is (\d+)")


def handoff_limit(skill_path=PLAN_WORK_SKILL):
    """The handoff limit as plan-work states it. Raises if the sentence moved."""
    with open(skill_path, encoding="utf8") as f:
        # The sentence wraps across lines in the skill, so match against the joined text.
        found = HANDOFF_LIMIT_SENTENCE.search(" ".join(f.read().split()))
    if not found:
        raise SystemExit(
            f"UNPARSEABLE: no handoff limit found in {os.path.normpath(skill_path)} — "
            "plan-work Step 1 must say 'The working limit for a single handoff is <n>'")
    return int(found.group(1))

REQUIRED = {
    "Epic": ["Goal", "Success measures", "In scope", "Out of scope", "Children"],
    "Story": ["Context", "Behavior", "Acceptance criteria", "Touch points", "Out of scope", "Dependencies"],
    "Task": ["Context", "Change", "Acceptance criteria", "Touch points", "Out of scope", "Dependencies"],
    "Bug": ["Environment", "Steps to reproduce", "Expected", "Actual", "Evidence",
            "Acceptance criteria", "Touch points", "Out of scope", "Dependencies"],
}
# MoSCoW as the DSDM Agile Project Framework defines it. The apostrophe is straight.
PRIORITIES = ["Must", "Should", "Could", "Won't"]
# Defect severity as the rule book's Phase 5 rates it, most severe first.
SEVERITIES = ["Critical", "High", "Medium", "Low"]
NFR_SECTION = "Non-functional requirements"
CHANGE_IMPACT = "Change impact"
SPEC_SECTIONS = ["Goal", "Behavior", "Change", "Acceptance criteria", "Expected", "Success measures", NFR_SECTION]
UNDECIDED = [r"\bTBD\b", r"\bTBC\b", r"\bTODO\b", r"\?\?", r"\betc\b", r"\be\.g\.", r"\band/or\b",
             r"\bas needed\b", r"\bas appropriate\b", r"\bif possible\b", r"\bwhere applicable\b",
             r"\binvestigate\b", r"\bexplore\b", r"\bconsider\b", r"\bdecide\b", r"\bdetermine whether\b"]
VAGUE = [r"\bgracefully\b", r"\bproperly\b", r"\bcorrectly\b", r"\bappropriate(ly)?\b", r"\buser-friendly\b",
         r"\bintuitive\b", r"\brobust\b", r"\bseamless(ly)?\b", r"\bfast\b", r"\bquickly\b",
         r"\befficient(ly)?\b", r"\bimprove[sd]?\b", r"\bbetter\b", r"\boptimi[sz]e[sd]?\b"]
SESSION_REFS = [r"\bas discussed\b", r"\bas mentioned\b", r"\bper (the )?above\b", r"\bsee above\b",
                r"\bearlier in (this|the) (chat|conversation|session)\b", r"\bwe agreed\b"]

# A local ID while drafting; Step 8 replaces it with the Jira key once the ticket exists.
HEADER = re.compile(r"^# \[(?P<id>[ESTB]\d+|[A-Z][A-Z0-9]+-\d+)\]\s+(?P<summary>.+?)\s*$")
META = re.compile(r"^(Type|Parent|Blocked by|Handoff|Labels|Priority|Severity|Goal|Jira):\s*(.*)$")
SECTION = re.compile(r"^## (.+?)\s*$")
VERIFY_TAG = r"\[verify:\s*([^@\]\s][^@\]]*?)\s*@\s*([^\]\s][^\]]*?)\s*\]"
AC = re.compile(r"^-\s+AC(\d+):\s+(.+?)\s*" + VERIFY_TAG + r"\s*$")
NFR = re.compile(r"^-\s+NFR(\d+):\s+(.*)$")
NFR_TAG = re.compile(VERIFY_TAG + r"\s*$")
NFR_TYPES = ("Epic", "Story")
GOAL_TYPES = ("Story", "Task")
GOAL_HEADER = "the Goal header"
# `<metric> <comparator> <number>`, read at the line's first comparator, the way an OpenSLO
# threshold pairs an operator with a value: a number anywhere else is not a threshold. The
# unit is prose, so ticket-adversary checks it, not this.
# Not the > of an arrow (->, =>), the = of one, or the = of !=.
COMPARATOR = re.compile(r"(?<![-=!])(?:<=|>=|≤|≥|<|>|=)(?!>)")
NUMBER = re.compile(r"\s*[-+]?[$€£]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)")
TOUCH = re.compile(r"^-\s+`?([^`\s]+)`?\s+\((modify|new|delete)\)\s*:?\s*(.*)$")
MEASURE = re.compile(r"^-\s+SM(\d+):\s+(.+?)\s*\[children:\s*([^\]\s][^\]]*)\]\s*$")
# Literal text the word checks skip: bracketed tags and code spans. A tag holding a backtick
# is not one: Step 8 could not wrap it in a code span, so it is checked as bare brackets.
TAG = re.compile(r"\[(?:verify|children):[^\]`]*\]")
CODE_SPAN = re.compile(r"`[^`]+`")
KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
LOCAL = re.compile(r"^[ESTB]\d+$")


def parse(text):
    items, cur, section = [], None, None
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("<!-- review round"):
            break  # review output is appended last and never linted
        m = HEADER.match(line)
        if m:
            cur = {"id": m["id"], "summary": m["summary"], "line": n, "meta": {}, "sections": {}, "stray": []}
            items.append(cur)
            section = None
        elif cur is None:
            continue
        elif SECTION.match(line):
            section = SECTION.match(line).group(1)
            cur["sections"].setdefault(section, [])
        elif section is None:
            m = META.match(line)
            if m:
                cur["meta"][m.group(1)] = m.group(2).strip()
            elif line.strip():
                cur["stray"].append(n)
        else:
            cur["sections"][section].append(line)
    return items


def body(lines):
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("<!--")]


# Backtick fences only: a ~~~ fence's tildes are text the read pairs as subscript.
FENCE = re.compile(r"^```")


def unfenced(lines):
    """(line, fenced) for each line: prose as body() keeps it, and a fenced block's lines
    verbatim, blank and indented ones included, since a fenced block is literal."""
    fenced, out = False, []
    for line in lines:
        line = line.rstrip("\r\n")
        if FENCE.match(line.strip()):
            out.append((line.strip(), True))
            fenced = not fenced
        elif fenced:
            out.append((line, True))
        else:
            out += [(l, False) for l in body([line])]
    return out


def prose_lines(lines):
    return [l for l, fenced in unfenced(lines) if not fenced]


def evidence_missing(repo, evidence):
    # The named path itself must exist: a file whose directory exists but whose name is a
    # typo is exactly the unfillable `Verified by` cell this catches. Prose evidence has no '/'.
    return "/" in evidence and not os.path.exists(os.path.join(repo, evidence))


def has_threshold(text):
    # Mask, not blank, each code span: a backticked metric still counts as a metric, and an
    # operator inside a span still does not count as the comparator.
    text = CODE_SPAN.sub(lambda m: "x" * len(m[0]), text)
    cmp = COMPARATOR.search(text)
    return bool(cmp and text[:cmp.start()].strip() and NUMBER.match(text, cmp.end()))


def without_literals(line):
    """The line without its tags and code spans, the text the word checks read."""
    return CODE_SPAN.sub("", TAG.sub("", line))


def ids(value):
    if not value or value.strip().lower() == "none":
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def lint(items, repo):
    errors, warns = [], []
    err = lambda i, c, m: errors.append(f"ERROR {i['id']} [{c}] {m}")
    warn = lambda i, c, m: warns.append(f"WARN  {i['id']} [{c}] {m}")
    by_id = {}
    for i in items:
        if i["id"] in by_id:
            err(i, "FORMAT", f"duplicate ID at line {i['line']}")
        by_id[i["id"]] = i

    created = {i["id"]: {m.group(1) for m in (TOUCH.match(l) for l in body(i["sections"].get("Touch points", [])))
                         if m and m.group(2) == "new"} for i in items}

    def upstream(iid, seen):
        for r in ids(by_id[iid]["meta"].get("Blocked by")):
            if r in by_id and r not in seen:
                seen.add(r)
                upstream(r, seen)
        return seen

    handoffs = {}
    for i in items:
        t = i["meta"].get("Type", "")
        if t not in REQUIRED:
            err(i, "FORMAT", f"Type must be one of {sorted(REQUIRED)}, got '{t}'")
            continue
        priority = i["meta"].get("Priority") or None
        if priority is None:
            if t != "Epic":
                err(i, "R12", f"missing Priority: — one of {', '.join(PRIORITIES)}")
        elif priority not in PRIORITIES:
            err(i, "R12", f"Priority must be one of {', '.join(PRIORITIES)}, got '{priority}'")
        severity = i["meta"].get("Severity") or None
        if t != "Bug":
            if severity:
                err(i, "B4", f"Severity: belongs on a Bug, not on this {t}")
        elif severity is None:
            err(i, "B4", f"missing Severity: — one of {', '.join(SEVERITIES)}")
        elif severity not in SEVERITIES:
            err(i, "B4", f"Severity must be one of {', '.join(SEVERITIES)}, got '{severity}'")
        for n in i["stray"]:
            # A header field is one line; a wrapped one would otherwise lose its tail unseen.
            err(i, "FORMAT", f"line {n} in the header is not a 'Field: value' line")
        if len(i["summary"]) > SUMMARY_MAX:
            err(i, "R1", f"summary is {len(i['summary'])} characters, max {SUMMARY_MAX}")
        if re.search(r"\band\b", i["summary"], re.I):
            warn(i, "R1", "summary contains 'and' — confirm it is one behavior")
        for s in REQUIRED[t]:
            if s not in i["sections"]:
                err(i, "FORMAT", f"missing '## {s}'")
            elif not body(i["sections"][s]):
                err(i, "FORMAT", f"'## {s}' is empty")
        if body(i["sections"].get("Open questions", [])):
            err(i, "R6", "Open questions has content — settle it before review")
        # A filled Jira: line means rewrite mode fetched a baselined ticket.
        jira_key = i["meta"].get("Jira", "")
        if jira_key and not body(i["sections"].get(CHANGE_IMPACT, [])):
            state = "empty" if CHANGE_IMPACT in i["sections"] else "missing"
            err(i, "R15", f"Jira: {jira_key} is filled and '## {CHANGE_IMPACT}' is {state} — "
                          "record what this rewrite changes")
        elif CHANGE_IMPACT in i["sections"] and not jira_key:
            err(i, "R15", f"'## {CHANGE_IMPACT}' belongs on a ticket whose Jira: line is filled")
        goal = i["meta"].get("Goal", "")
        if goal and t not in GOAL_TYPES:
            err(i, "R14", f"Goal: belongs on a Story or Task, not on this {t}")
        # The Goal: header reaches Jira as the description's first line, so it is prose too.
        prose = dict(i["sections"], **({GOAL_HEADER: [goal]} if goal else {}))
        for s, lines in prose.items():
            for line in prose_lines(lines):
                for p in SESSION_REFS:
                    if re.search(p, line, re.I):
                        err(i, "R10", f"refers to the authoring session in {s}: {line[:80]}")
        # What Step 8 sends must come back from jira_get_issue as sent; templates.md says why.
        # The change-impact comment goes through the same connector write.
        for sent in (step8_lines(i), comment_lines(i)):
            for change in line_changes(sent, roundtrip("\n".join(sent))):
                # The read's own placeholders can surface when a {code} macro swallows text.
                err(i, "JIRA", f"Jira's round trip changes {change}".replace("\x00", "")[:200])
        for s in SPEC_SECTIONS + [GOAL_HEADER]:
            for line in prose_lines(prose.get(s, [])):
                text = without_literals(line)
                for p in UNDECIDED:
                    if re.search(p, text, re.I):
                        err(i, "R6", f"'{re.search(p, text, re.I).group(0)}' in {s}: {line[:80]}")
                for p in VAGUE:
                    if re.search(p, text, re.I):
                        warn(i, "R7", f"vague '{re.search(p, text, re.I).group(0)}' in {s}: {line[:80]}")
        nfr_lines = body(i["sections"].get(NFR_SECTION, []))
        if NFR_SECTION in i["sections"] and t not in NFR_TYPES:
            err(i, "R13", f"'## {NFR_SECTION}' belongs on an Epic or Story, not on this {t}")
            nfr_lines = []
        elif NFR_SECTION in i["sections"] and not nfr_lines:
            err(i, "R13", f"'## {NFR_SECTION}' is empty")
        for line in nfr_lines:
            m = NFR.match(line)
            if not m:
                err(i, "R13", f"not '- NFRn: <metric> <comparator> <number><unit> <condition> "
                              f"[verify: tier @ evidence]': {line[:80]}")
                continue
            num, rest = m.groups()
            tag = NFR_TAG.search(rest)
            if not tag:
                err(i, "R13", f"NFR{num} has no [verify: tier @ evidence] tag")
            if not has_threshold(rest[:tag.start()] if tag else rest):
                err(i, "R13", f"NFR{num} has no '<metric> <comparator> <number>' threshold")
            if tag and evidence_missing(repo, tag.group(2)):
                err(i, "R13", f"NFR{num} evidence {tag.group(2)} does not exist in the repo")
        for ref in ids(i["meta"].get("Blocked by")) + ids(i["meta"].get("Parent")):
            if LOCAL.match(ref):
                if ref not in by_id:
                    err(i, "R8", f"unknown ID {ref}")
            elif not KEY.match(ref):
                err(i, "FORMAT", f"'{ref}' is neither a draft ID nor a Jira key")

        if t == "Epic":
            mapped = set()
            for line in body(i["sections"].get("Success measures", [])):
                m = MEASURE.match(line)
                if not m:
                    err(i, "E2", f"not '- SMn: ... [children: ...]': {line[:80]}")
                    continue
                for c in ids(m.group(3)):
                    mapped.add(c)
                    if c not in by_id:
                        err(i, "E2", f"SM{m.group(1)} names unknown child {c}")
            for o in items:
                if o["meta"].get("Parent") == i["id"] and o["id"] not in mapped \
                        and "enabling" not in o["meta"].get("Labels", "").lower():
                    err(i, "E3", f"child {o['id']} maps to no success measure and is not 'enabling'")
            continue

        if t in GOAL_TYPES and not ids(i["meta"].get("Parent")) and not goal:
            err(i, "R14", "no Parent: and no Goal: — name the outcome this ticket serves")

        h = i["meta"].get("Handoff", "")
        if not h:
            err(i, "R2", "missing Handoff label")
        else:
            handoffs.setdefault(h, []).append(i["id"])

        acs = body(i["sections"].get("Acceptance criteria", []))
        for line in acs:
            m = AC.match(line)
            if not m:
                err(i, "R7", f"not '- ACn: ... [verify: tier @ evidence]': {line[:80]}")
                continue
            num, text, _tier, evidence = m.groups()
            clauses = len(re.findall(r"[,;]", CODE_SPAN.sub("", text))) + 1
            if clauses > 1:
                warn(i, "R7", f"AC{num} is {clauses} plan-work rows (split on , and ;) — each needs its own verification")
            if evidence_missing(repo, evidence):
                err(i, "R7", f"AC{num} evidence {evidence} does not exist in the repo")
        if t == "Bug" and not any(re.search(r"\bRegression:", l) for l in acs):
            err(i, "B2", "no AC marked 'Regression:'")

        mine = upstream(i["id"], set())
        for line in body(i["sections"].get("Touch points", [])):
            m = TOUCH.match(line)
            if not m:
                err(i, "R3", f"not '- path (modify|new|delete): purpose': {line[:80]}")
                continue
            path, kind = m.group(1), m.group(2)
            full = os.path.join(repo, path)
            if kind in ("modify", "delete") and not os.path.exists(full) \
                    and not any(path in created[u] for u in mine):
                err(i, "R3", f"{path} ({kind}) does not exist and no Blocked-by ticket creates it")
            if kind == "new" and os.path.exists(full):
                err(i, "R3", f"{path} is marked (new) but exists")

    limit = handoff_limit()
    for h, members in handoffs.items():
        if len(members) > limit:
            errors.append(f"ERROR {members[0]} [R2] handoff '{h}' has {len(members)} tickets, "
                          f"plan-work's limit is {limit}: {', '.join(members)}")

    graph = {i["id"]: [r for r in ids(i["meta"].get("Blocked by")) if r in by_id] for i in items}
    state = {}

    def visit(n, path):
        state[n] = 1
        for m in graph[n]:
            if state.get(m) == 1:
                errors.append(f"ERROR {n} [E4] Blocked-by cycle: {' -> '.join(path + [n, m])}")
            elif not state.get(m):
                visit(m, path + [n])
        state[n] = 2

    for n in graph:
        if not state.get(n):
            visit(n, [])
    return errors, warns


def jira_line(line):
    """The line as Step 8 writes it: each [verify:] or [children:] tag inside a code span."""
    parts = re.split(f"({CODE_SPAN.pattern})", line)
    return "".join(p if n % 2 else TAG.sub(lambda m: f"`{m[0]}`", p) for n, p in enumerate(parts))


def normalized(lines):
    """Lines as Jira's round trip leaves them unchanged: prose without blanks and with every
    ordered item `1.`; fenced code exactly as written."""
    return [l if fenced else re.sub(r"^\d+\.\s", "1. ", l) for l, fenced in unfenced(lines)]


def step8_lines(item):
    """The description Step 8 writes for a draft item: one entry per prose line, and a
    fenced block's lines verbatim."""
    goal = item["meta"].get("Goal")
    lines = [jira_line(f"Goal: {goal}")] if goal else []
    for s, sec in item["sections"].items():
        if s not in ("Open questions", CHANGE_IMPACT):
            lines += [f"## {s}"] + [l if fenced else jira_line(l) for l, fenced in unfenced(sec)]
    return lines


def comment_lines(item):
    """The change-impact comment Step 8 posts for a rewritten item, written as the
    description is."""
    return [l if fenced else jira_line(l) for l, fenced in unfenced(item["sections"].get(CHANGE_IMPACT, []))]


def readback(item, fetched):
    """Each line Step 8 wrote for this draft item that the description Jira returned lacks
    or altered."""
    return line_changes(step8_lines(item), fetched)


def changed_lines(sent, fetched):
    """The sent lines that did not come back unchanged."""
    want, got = normalized(sent.splitlines()), normalized(fetched.splitlines())
    diff = difflib.SequenceMatcher(None, want, got, autojunk=False)
    return {w for op, i1, i2, _, _ in diff.get_opcodes() if op != "equal" for w in want[i1:i2]}


def line_changes(sent, fetched):
    """A line diff of what was sent against what came back, both normalized."""
    want, got = normalized(sent), normalized(fetched.splitlines())
    diff = difflib.SequenceMatcher(None, want, got, autojunk=False)
    missing = []
    for op, i1, i2, j1, j2 in diff.get_opcodes():
        if op == "equal":
            continue
        sent, back = want[i1:i2], got[j1:j2]
        missing += [f"'{w}' came back as '{g}'" for w, g in zip(sent, back)]
        missing += [f"'{w}'" for w in sent[len(back):]]
        missing += [f"extra '{g}'" for g in back[len(sent):]]
    return missing


def readback_cli_test(cases, scratch):
    """Step 8 runs --readback on a draft whose headers already hold Jira keys, and on a
    rewritten one whose header keeps its local ID, whose `Jira:` line holds the key, and
    whose `## Change impact` Step 8 posts as a comment rather than in the description."""
    draft_text = open(os.path.join(cases, "_draft.md"), encoding="utf8").read()
    keyed = os.path.join(scratch, "keyed.md")
    with open(keyed, "w", encoding="utf8") as f:
        f.write(draft_text.replace("[S1]", "[AB-2]").replace("[E1]", "[AB-1]"))
    rewritten = os.path.join(scratch, "rewritten.md")
    with open(rewritten, "w", encoding="utf8") as f:
        f.write(re.sub(r"(# \[S1\].*\n(?:.+\n)*?)Jira:\n", r"\1Jira: AB-3\n", draft_text, count=1)
                .replace("## Open questions\n", "## Change impact\n- AC1 changed: returned 201; now returns 200\n\n"
                         "## Open questions\n", 1))
    failed = 0
    for draft, key, case, want in ((keyed, "AB-2", "faithful.md", 0), (keyed, "AB-2", "lost-span.md", 1),
                                   (rewritten, "AB-3", "faithful.md", 0), (keyed, "AB-9", "faithful.md", 2),
                                   (keyed, "AB-2", "absent.md", 2)):
        with contextlib.redirect_stdout(io.StringIO()):
            got = main([draft, "--readback", key, os.path.join(cases, case)])
        ok = got == want
        print(f"{'ok  ' if ok else 'FAIL'} --readback {key} {case}: exit {got}, want {want}")
        failed += not ok
    return failed


FINDING = re.compile(r"^(ERROR|WARN)\s+\S+ \[([^\]]+)\]")
# One key per code, warnings as warn:CODE. check_readme.py lists codes instead
# (errors=R1,R1); both scripts are stdlib-only and standalone, so neither imports the other.
EXPECT = re.compile(r"<!-- expect((?: [\w:]+=\d+)*) -->")


def code_counts(findings):
    """{code: n} for errors and {warn:code: n} for warnings, as fixtures declare them."""
    counts = {}
    for f in findings:
        m = FINDING.match(f)
        key = "unparsed" if not m else m[2] if m[1] == "ERROR" else f"warn:{m[2]}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def declared_counts(text):
    """The counts a fixture's line 1 declares, or a string saying why there are none."""
    m = EXPECT.match(text)
    if not m:
        return "line 1 has no <!-- expect CODE=n ... --> header"
    pairs = [p.split("=") for p in m.group(1).split()]
    keys = [k for k, _ in pairs]
    if len(set(keys)) < len(keys):
        return f"a code is declared twice: {' '.join(keys)}"
    if any(int(v) == 0 for _, v in pairs):
        return "a code is declared =0; leave it out instead"
    if "unparsed" in keys:
        return "unparsed is not a code; the linter printed a line it should not have"
    return {k: int(v) for k, v in pairs}


def fixture_matches(text, findings):
    """(ok, why) for a fixture's declared counts against what the linter found."""
    want, got = declared_counts(text), code_counts(findings)
    if isinstance(want, str):
        return False, want
    show = lambda c: " ".join(f"{k}={v}" for k, v in sorted(c.items())) or "nothing"
    return want == got, f"expected {show(want)}, got {show(got)}"


def counts_test():
    """The comparison itself: each way a fixture could pass while a check misfires, and the
    reason a malformed header gives."""
    cases = (("the right total under the wrong code", "<!-- expect R12=1 -->", ["ERROR S1 [R13] x"], ""),
             ("a code the fixture does not declare", "<!-- expect R12=1 -->",
              ["ERROR S1 [R12] x", "WARN  S1 [R7] y"], ""),
             ("a warning counted as an error", "<!-- expect R7=1 -->", ["WARN  S1 [R7] y"], ""),
             ("a finding the linter could not have printed", "<!-- expect -->", ["R12 x"], ""),
             ("no declaration at all", "# [S1] x", [], "no <!-- expect"),
             ("a code declared twice", "<!-- expect R12=1 R12=1 -->", ["ERROR S1 [R12] x"], "twice"),
             ("a code declared =0", "<!-- expect R12=0 -->", [], "=0"),
             ("unparsed declared as a code", "<!-- expect unparsed=1 -->", ["R12 x"], "not a code"))
    failed = 0
    for name, header, findings, reason in cases:
        ok, why = fixture_matches(header, findings)
        good = not ok and reason in why
        print(f"{'ok  ' if good else 'FAIL'} counts: {name} fails the fixture")
        failed += not good
    return failed


def self_test():
    """Each fixture declares its exact count per code on line 1: <!-- expect R12=2 warn:R7=1 -->."""
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    repo = tempfile.mkdtemp()
    try:
        # Every path the fixtures cite and expect to exist. A fixture citing anything else
        # is asserting that the path is absent — `tests/missing/dir/hash.test.ts` in
        # clauses.md and `tests/perf/coldstart.test.ts` in nfr.md are deliberately not
        # here, and clean.md must cite only these.
        for f in ("src/auth/routes.ts", "src/auth/config.ts", "src/auth/tokens.ts",
                  "tests/auth/button.test.ts", "tests/auth/empty.test.ts",
                  "tests/auth/export.test.ts", "tests/auth/limit.test.ts",
                  "tests/auth/login.test.ts", "tests/auth/refresh.test.ts",
                  "tests/auth/signin.test.ts", "tests/auth/tokens-table.test.ts",
                  "tests/contacts/import.test.ts"):
            os.makedirs(os.path.join(repo, os.path.dirname(f)), exist_ok=True)
            open(os.path.join(repo, f), "w").close()
        failed = 0
        for name in sorted(os.listdir(here)):
            if name.startswith(".") or os.path.isdir(os.path.join(here, name)):
                continue  # editor metadata, and readback/ below; any other file is a fixture
            text = open(os.path.join(here, name), encoding="utf8").read()
            errors, warns = lint(parse(text), repo)
            ok, why = fixture_matches(text, errors + warns)
            print(f"{'ok  ' if ok else 'FAIL'} {name}: {why}")
            if not ok:
                failed += 1
                print("\n".join("     " + l for l in errors + warns))
        # Each readback case is a description as `jira_get_issue` returns it for an item in
        # _draft.md: <!-- expect id=S1 missing=N -->. probe-*.md are captured responses.
        cases = os.path.join(here, "readback")
        draft = {i["id"]: i for i in parse(open(os.path.join(cases, "_draft.md"), encoding="utf8").read())}
        for name in sorted(n for n in os.listdir(cases) if not n.startswith((".", "_"))):
            text = open(os.path.join(cases, name), encoding="utf8").read()
            want = re.match(r"<!-- expect id=(\S+) missing=(\d+) -->", text)
            got = readback(draft[want.group(1)], text) if want and want.group(1) in draft else None
            ok = got is not None and len(got) == int(want.group(2))
            print(f"{'ok  ' if ok else 'FAIL'} readback/{name}: missing={'?' if got is None else len(got)}")
            if not ok:
                failed += 1
                print("\n".join("     " + l for l in got or []))
        failed += readback_cli_test(cases, repo)
        failed += counts_test()
        # Pins the pieces of the round trip not vendored to what Jira Cloud returned.
        for n, (sent, live) in enumerate(PROBES, 1):
            model = roundtrip(sent)
            ok = changed_lines(sent, model) == changed_lines(sent, live)
            print(f"{'ok  ' if ok else 'FAIL'} jira round trip agrees with live probe {n} on every line")
            failed += not ok
        return 1 if failed else 0
    finally:
        shutil.rmtree(repo)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("draft", nargs="?")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--readback", nargs=2, metavar=("ID", "FETCHED"))
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.draft:
        ap.error("a draft path is required")
    try:
        items = parse(open(a.draft, encoding="utf8").read())
        fetched = open(a.readback[1], encoding="utf8").read() if a.readback else None
    except OSError as e:
        print(f"UNPARSEABLE: {e}")
        return 2
    if not items:
        print("UNPARSEABLE: no tickets found — headers look like '# [S1] Summary' or '# [AB-1] Summary'")
        return 2
    if a.readback:
        # The header holds the key once Step 8 has created or fetched the ticket; a header that
        # still holds a local ID is found by its `Jira:` line.
        item = next((i for i in items if a.readback[0] in (i["id"], i["meta"].get("Jira"))), None)
        if item is None:
            print(f"UNPARSEABLE: no header or Jira: line names {a.readback[0]} in {a.draft}")
            return 2
        missing = readback(item, fetched)
        for m in missing:
            print(f"MISSING {a.readback[0]}: {m}")
        print(f"SUMMARY: {a.readback[0]}, missing from {a.readback[1]}: {len(missing)}")
        return 1 if missing else 0
    errors, warns = lint(items, os.path.abspath(a.repo))
    print("\n".join(errors + warns))
    print(f"SUMMARY: {len(items)} tickets, {len(errors)} errors, {len(warns)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
