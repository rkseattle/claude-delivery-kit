#!/usr/bin/env python3
"""The reviewer set ship-pr requests, and the approval ci-green waits for. Standard library only.

Called by both skills/ship-pr/SKILL.md (Step 4) and skills/ci-green/SKILL.md (Step 5).

    review_gate.py reviewer-set --reviewers VALUE [--author LOGIN]
        prints the set, comma-separated, or `none`; without --author, the configured set
    review_gate.py approval --head SHA --author LOGIN < REVIEWS
        REVIEWS is `gh api --paginate .../pulls/<pr>/reviews` output; prints
        `approved <login>`, `blocked <login,...>`, or `outstanding`; exit 0 only if approved
    review_gate.py --self-test     runs every case below; exit 0 only if each one matches

Exit 2 is unparseable input, never a verdict.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "gates", "scripts"))
from project_rules import (cli_case, error_of, is_unset,  # noqa: E402  shared with the kit's scripts
                           report)
# COLLABORATOR includes read-only collaborators, whom a required-review rule would not count;
# branch protection, not this script, is what blocks a merge.
COUNTED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
# COMMENTED and PENDING never change a reviewer's standing. GitHub marks a dismissed review
# DISMISSED in place, and a dismissed review no longer counts at all.
DECISIVE_STATES = {"APPROVED", "CHANGES_REQUESTED"}


def reviewer_set(reviewers, author=None):
    """The configured reviewers minus the author, or [] for none."""
    if is_unset(reviewers):
        return []
    value = reviewers.strip()
    resolved = []
    for entry in value.split(","):
        login = entry.strip()
        if not login or login.lower() in (r.lower() for r in resolved):
            continue
        if author and login.lower() == author.lower():
            continue
        resolved.append(login)
    return resolved


def parse_reviews(text):
    """Every review in gh's output: one array per page, concatenated, or --slurp's array of arrays."""
    if not text.strip():
        raise ValueError("no output at all, so the gh call failed before writing a body")
    decoder = json.JSONDecoder()
    reviews, position = [], 0
    while True:
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            return reviews
        value, position = decoder.raw_decode(text, position)
        if not isinstance(value, list):
            raise ValueError("the output is not a JSON array — an error body, most likely")
        pages = value if value and all(isinstance(page, list) for page in value) else [value]
        for page in pages:
            if not isinstance(page, list) or not all(well_formed(r) for r in page):
                raise ValueError("a page of reviews is not a JSON array of review objects")
            reviews.extend(page)


def well_formed(review):
    """Every field approval() reads has the type the List reviews endpoint documents."""
    if not isinstance(review, dict):
        return False
    user = review.get("user")
    if user is not None and not (isinstance(user, dict)
                                 and isinstance(user.get("login"), str) and user["login"]
                                 and isinstance(user.get("type"), (str, type(None)))):
        return False
    expected = {"id": int, "state": str, "commit_id": str, "submitted_at": str,
                "author_association": str}
    return all(review.get(field) is None or isinstance(review.get(field), kind)
               and not isinstance(review.get(field), bool)
               for field, kind in expected.items())


def approval(reviews, head, author):
    """GitHub's review decision for the head commit, counting only the repo's own people."""
    standing = {}
    # submitted_at, then id, orders reviews by submission — compared as strings, which
    # holds because GitHub writes every timestamp in UTC with a Z suffix — so "latest wins" holds whatever
    # order the pages arrive in. A review with no submitted_at sorts first; the stable sort
    # keeps reviews with equal keys in the order given.
    for review in sorted(reviews, key=lambda r: (r.get("submitted_at") or "", r.get("id") or 0)):
        user = review.get("user") or {}
        login = user.get("login") or ""
        if (user.get("type") != "User"
                or review.get("author_association") not in COUNTED_ASSOCIATIONS
                or login.lower() == author.lower()
                or review.get("state") not in DECISIVE_STATES):
            continue
        standing[login] = (review["state"], review.get("commit_id"))
    blocking = [login for login, (state, _) in standing.items() if state == "CHANGES_REQUESTED"]
    if blocking:
        return "blocked " + ",".join(blocking)
    for login, (state, commit) in standing.items():
        if state == "APPROVED" and commit == head:
            return "approved " + login
    return "outstanding"


def review(login, state, commit="head", kind="User", association="COLLABORATOR"):
    return {"user": {"login": login, "type": kind}, "author_association": association,
            "state": state, "commit_id": commit}


APPROVAL_CASES = [
    ("an approval of the head", [review("ana", "APPROVED")], "approved ana"),
    ("an approval of an older commit", [review("ana", "APPROVED", "old")], "outstanding"),
    ("a fresh approval after a stale one",
     [review("ana", "APPROVED", "old"), review("ana", "APPROVED")], "approved ana"),
    ("a bot's approval", [review("ci[bot]", "APPROVED", kind="Bot")], "outstanding"),
    ("a drive-by account's approval", [review("eve", "APPROVED", association="NONE")],
     "outstanding"),
    ("the author approving their own PR", [review("Rob", "APPROVED")], "outstanding"),
    ("a later changes request from the approver",
     [review("ana", "APPROVED"), review("ana", "CHANGES_REQUESTED")], "blocked ana"),
    ("a second reviewer still blocking",
     [review("ana", "APPROVED"), review("ben", "CHANGES_REQUESTED", "old")], "blocked ben"),
    ("a comment after an approval", [review("ana", "APPROVED"), review("ana", "COMMENTED")],
     "approved ana"),
    ("a dismissed approval", [review("ana", "DISMISSED")], "outstanding"),
    ("an approval standing after a dismissed changes request",
     [review("ana", "APPROVED"), review("ana", "DISMISSED")], "approved ana"),
    ("reviews out of submission order",
     [dict(review("ana", "APPROVED"), submitted_at="2026-01-02T00:00:00Z"),
      dict(review("ana", "CHANGES_REQUESTED"), submitted_at="2026-01-01T00:00:00Z")],
     "approved ana"),
    ("submission order over id order",
     [dict(review("ana", "APPROVED"), id=1, submitted_at="2026-01-02T00:00:00Z"),
      dict(review("ana", "CHANGES_REQUESTED"), id=2, submitted_at="2026-01-01T00:00:00Z")],
     "approved ana"),
    ("a review with no submitted_at sorts first",
     [dict(review("ana", "APPROVED"), submitted_at="2026-01-01T00:00:00Z"),
      review("ana", "CHANGES_REQUESTED")], "approved ana"),
    ("reviews out of id order",
     [dict(review("ana", "APPROVED"), id=2), dict(review("ana", "CHANGES_REQUESTED"), id=1)],
     "approved ana"),
    ("an approval after a changes request",
     [review("ana", "CHANGES_REQUESTED", "old"), review("ana", "APPROVED")], "approved ana"),
    ("no reviews at all", [], "outstanding"),
    ("a bot's changes request", [review("ana", "APPROVED"),
                                 review("ci[bot]", "CHANGES_REQUESTED", kind="Bot")], "approved ana"),
    ("a drive-by account's changes request",
     [review("ana", "APPROVED"), review("eve", "CHANGES_REQUESTED", association="NONE")],
     "approved ana"),
    ("a dismissed changes request",
     [review("ben", "DISMISSED"), review("ana", "APPROVED")], "approved ana"),
    ("a comment after a changes request",
     [review("ana", "APPROVED"), review("ben", "CHANGES_REQUESTED"), review("ben", "COMMENTED")],
     "blocked ben"),
    ("one stale approval and one of the head",
     [review("ana", "APPROVED", "old"), review("ben", "APPROVED")], "approved ben"),
    ("a deleted account's review",
     [{"user": None, "author_association": "NONE", "state": "APPROVED", "commit_id": "head"}],
     "outstanding"),
]

PAGINATION_CASES = [
    ("two pages concatenated", '[{}]\n[{}]', 2),
    ("--slurp's array of pages", '[[{}],[{}, {}]]', 3),
    ("one empty page", '[]', 0),
]

APPROVED_REVIEW = json.dumps([review("ana", "APPROVED")])
# The skills read what main prints and how it exits, so those are tested as well.
CLI_CASES = [
    ("reviewer-set prints none", ["reviewer-set", "--reviewers", "none"], "", "none", 0),
    ("reviewer-set prints the set", ["reviewer-set", "--reviewers", "ana, rob", "--author", "rob"],
     "", "ana", 0),
    ("an approval exits 0", ["approval", "--head", "head", "--author", "rob"], APPROVED_REVIEW,
     "approved ana", 0),
    ("no approval exits 1", ["approval", "--head", "other", "--author", "rob"], APPROVED_REVIEW,
     "outstanding", 1),
    ("a changes request exits 1", ["approval", "--head", "head", "--author", "rob"],
     json.dumps([review("ana", "CHANGES_REQUESTED")]), "blocked ana", 1),
    ("no subcommand exits 2", [], "", "", 2),
    ("empty output exits 2", ["approval", "--head", "head", "--author", "rob"], "", "", 2),
    ("an error body exits 2", ["approval", "--head", "head", "--author", "rob"],
     '{"message": "Not Found"}', "", 2),
    ("a bare scalar exits 2", ["approval", "--head", "head", "--author", "rob"], "5", "", 2),
    ("a numeric login exits 2", ["approval", "--head", "head", "--author", "rob"],
     '[{"user": {"login": 5, "type": "User"}, "state": "APPROVED"}]', "", 2),
    ("a non-string state exits 2", ["approval", "--head", "head", "--author", "rob"],
     '[{"user": {"login": "ana", "type": "User"}, "state": ["APPROVED"]}]', "", 2),
    ("a review with no login exits 2", ["approval", "--head", "head", "--author", "rob"],
     '[{"user": {"type": "User"}, "author_association": "OWNER", "state": "APPROVED",'
     ' "commit_id": "head"}]', "", 2),
    ("an empty login exits 2", ["approval", "--head", "head", "--author", "rob"],
     '[{"user": {"login": "", "type": "User"}, "state": "APPROVED"}]', "", 2),
    ("a boolean id exits 2", ["approval", "--head", "head", "--author", "rob"],
     '[{"id": true, "state": "APPROVED"}]', "", 2),
    ("a numeric commit_id exits 2", ["approval", "--head", "head", "--author", "rob"],
     '[{"state": "APPROVED", "commit_id": 7}]', "", 2),
    ("a numeric submitted_at exits 2", ["approval", "--head", "head", "--author", "rob"],
     '[{"state": "APPROVED", "submitted_at": 7}]', "", 2),
    ("a numeric author_association exits 2", ["approval", "--head", "head", "--author", "rob"],
     '[{"state": "APPROVED", "author_association": 7}]', "", 2),
    ("a numeric user type exits 2", ["approval", "--head", "head", "--author", "rob"],
     '[{"user": {"login": "ana", "type": 7}, "state": "APPROVED"}]', "", 2),
    ("mixed id types exit 2", ["approval", "--head", "head", "--author", "rob"],
     '[{"id": 1, "state": "APPROVED"}, {"id": "2", "state": "APPROVED"}]', "", 2),
    ("a leading dash in reviewers", ["reviewer-set", "--reviewers=-ana", "--author", "rob"], "",
     "-ana", 0),
]

REVIEWER_SET_CASES = [
    ("none", "none", "rob", []),
    ("an empty value", "", "rob", []),
    ("a missing key", None, "rob", []),
    ("a <placeholder>", "<comma-separated GitHub logins or org/team slugs, or none>", "rob", []),
    ("whitespace around entries", " ana , org/team ", "rob", ["ana", "org/team"]),
    ("the author, in another case", "ROB,ana", "rob", ["ana"]),
    ("only the author", "rob", "Rob", []),
    ("a repeated login", "ana,Ana", "rob", ["ana"]),
    ("empty entries", ",,", "rob", []),
    ("no author given yet", "rob,ana", None, ["rob", "ana"]),
]


def self_test():
    failures = 0
    for name, reviews, expected in APPROVAL_CASES:
        got = approval(reviews, "head", "rob")
        failures += report("approval", name, got, expected)
    for name, text, expected in PAGINATION_CASES:
        failures += report("pages", name, len(parse_reviews(text)), expected)
    for name, text in [("unparseable output", "not json"), ("empty output", "  \n"),
                       ("a page of numbers", "[1]"), ("a scalar after a page", "[[{}], 5]"),
                       ("a review whose user is a string", '[{"user": "x"}]')]:
        failures += report("pages", name, error_of(parse_reviews, text), "ValueError")
    for name, value, author, expected in REVIEWER_SET_CASES:
        failures += report("reviewer-set", name, reviewer_set(value, author), expected)
    for name, arguments, stdin, expected_output, expected_exit in CLI_CASES:
        failures += cli_case(os.path.abspath(__file__), name, arguments, expected_output,
                             expected_exit, exact=True, input=stdin)
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    resolve = commands.add_parser("reviewer-set")
    resolve.add_argument("--reviewers", default="")
    resolve.add_argument("--author")
    decide = commands.add_parser("approval")
    decide.add_argument("--head", required=True)
    decide.add_argument("--author", required=True)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.command == "reviewer-set":
        print(",".join(reviewer_set(args.reviewers, args.author)) or "none")
        return 0
    if args.command == "approval":
        try:
            reviews = parse_reviews(sys.stdin.read())
        except ValueError as error:
            print(f"UNPARSEABLE reviews: {error}", file=sys.stderr)
            return 2
        verdict = approval(reviews, args.head, args.author)
        print(verdict)
        return 0 if verdict.startswith("approved") else 1
    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
