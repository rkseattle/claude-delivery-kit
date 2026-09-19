#!/usr/bin/env python3
"""Lint a write-tickets draft. Standard library only.

    lint_draft.py DRAFT.md [--repo ROOT]   exit 0 clean, 1 errors, 2 unparseable
    lint_draft.py --self-test              runs the fixtures; exit 0 only if every count matches

Checks what a script can settle. Whether a ticket is plannable is ticket-adversary's call.
"""
import argparse
import os
import re
import shutil
import sys
import tempfile

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
SPEC_SECTIONS = ["Behavior", "Change", "Acceptance criteria", "Expected", "Success measures"]
UNDECIDED = [r"\bTBD\b", r"\bTBC\b", r"\bTODO\b", r"\?\?", r"\betc\b", r"\be\.g\.", r"\band/or\b",
             r"\bas needed\b", r"\bas appropriate\b", r"\bif possible\b", r"\bwhere applicable\b",
             r"\binvestigate\b", r"\bexplore\b", r"\bconsider\b", r"\bdecide\b", r"\bdetermine whether\b"]
VAGUE = [r"\bgracefully\b", r"\bproperly\b", r"\bcorrectly\b", r"\bappropriate(ly)?\b", r"\buser-friendly\b",
         r"\bintuitive\b", r"\brobust\b", r"\bseamless(ly)?\b", r"\bfast\b", r"\bquickly\b",
         r"\befficient(ly)?\b", r"\bimprove[sd]?\b", r"\bbetter\b", r"\boptimi[sz]e[sd]?\b"]
SESSION_REFS = [r"\bas discussed\b", r"\bas mentioned\b", r"\bper (the )?above\b", r"\bsee above\b",
                r"\bearlier in (this|the) (chat|conversation|session)\b", r"\bwe agreed\b"]

HEADER = re.compile(r"^# \[(?P<id>[ESTB]\d+)\]\s+(?P<summary>.+?)\s*$")
META = re.compile(r"^(Type|Parent|Blocked by|Handoff|Labels|Jira):\s*(.*)$")
SECTION = re.compile(r"^## (.+?)\s*$")
AC = re.compile(r"^-\s+AC(\d+):\s+(.+?)\s*\[verify:\s*([^@\]]+?)\s*@\s*([^\]]+?)\s*\]\s*$")
TOUCH = re.compile(r"^-\s+`?([^`\s]+)`?\s+\((modify|new|delete)\)\s*:?\s*(.*)$")
MEASURE = re.compile(r"^-\s+SM(\d+):\s+(.+?)\s*\[children:\s*([^\]]+)\]\s*$")
KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
LOCAL = re.compile(r"^[ESTB]\d+$")


def parse(text):
    items, cur, section = [], None, None
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("<!-- review round"):
            break  # review output is appended last and never linted
        m = HEADER.match(line)
        if m:
            cur = {"id": m["id"], "summary": m["summary"], "line": n, "meta": {}, "sections": {}}
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
        else:
            cur["sections"][section].append(line)
    return items


def body(lines):
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("<!--")]


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
        for s, lines in i["sections"].items():
            for line in body(lines):
                for p in SESSION_REFS:
                    if re.search(p, line, re.I):
                        err(i, "R10", f"refers to the authoring session in {s}: {line[:80]}")
        for s in SPEC_SECTIONS:
            for line in body(i["sections"].get(s, [])):
                text = re.sub(r"\[verify:[^\]]*\]|`[^`]*`", "", line)
                for p in UNDECIDED:
                    if re.search(p, text, re.I):
                        err(i, "R6", f"'{re.search(p, text, re.I).group(0)}' in {s}: {line[:80]}")
                for p in VAGUE:
                    if re.search(p, text, re.I):
                        warn(i, "R7", f"vague '{re.search(p, text, re.I).group(0)}' in {s}: {line[:80]}")
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
            clauses = len(re.findall(r"[,;]", re.sub(r"`[^`]*`", "", text))) + 1
            if clauses > 1:
                warn(i, "R7", f"AC{num} is {clauses} plan-work rows (split on , and ;) — each needs its own verification")
            if "/" in evidence:
                # R7 wants the named path itself to exist: a file whose directory exists but
                # whose name is a typo is exactly the unfillable `Verified by` cell this catches.
                if not os.path.exists(os.path.join(repo, evidence)):
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


def self_test():
    """Each fixture declares its expected counts on line 1: <!-- expect errors=N warnings=M -->."""
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    repo = tempfile.mkdtemp()
    try:
        # Every path the fixtures cite and expect to exist. A fixture citing anything else
        # is asserting that the path is absent — `tests/missing/dir/hash.test.ts` in
        # clauses.md is deliberately not here, and clean.md must cite only these.
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
            text = open(os.path.join(here, name), encoding="utf8").read()
            want = re.match(r"<!-- expect errors=(\d+) warnings=(\d+) -->", text)
            errors, warns = lint(parse(text), repo)
            got = (len(errors), len(warns))
            ok = want and got == (int(want.group(1)), int(want.group(2)))
            print(f"{'ok  ' if ok else 'FAIL'} {name}: errors={got[0]} warnings={got[1]}")
            if not ok:
                failed += 1
                print("\n".join("     " + l for l in errors + warns))
        return 1 if failed else 0
    finally:
        shutil.rmtree(repo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft", nargs="?")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.draft:
        ap.error("a draft path is required")
    try:
        items = parse(open(a.draft, encoding="utf8").read())
    except OSError as e:
        print(f"UNPARSEABLE: {e}")
        return 2
    if not items:
        print("UNPARSEABLE: no tickets found — headers look like '# [S1] Summary'")
        return 2
    errors, warns = lint(items, os.path.abspath(a.repo))
    print("\n".join(errors + warns))
    print(f"SUMMARY: {len(items)} tickets, {len(errors)} errors, {len(warns)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
