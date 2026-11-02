#!/usr/bin/env python3
"""Feature-design checks, so the skill settles none of them by eye. Standard library only.

Written for the design-feature skill to run before it writes a design.

    design_check.py dirs --config PATH
        `ok` when design_dir and adr_dir are each a relative path inside the repository, as
        release_dir must be, and not one directory, as project_rules.design_dirs rules;
        `ok\tadr_dir not configured` when adr_dir is unset, which
        gates/design-exit.md fails only for a design with a costly-to-reverse choice
    design_check.py slug [--title TITLE]
        the design's <slug> for the title, or standard input: project_rules.slug_of fitted
        to SLUG_MAX; INVALID when no letter or digit is left
    design_check.py base-tree add COMMIT
        once COMMIT resolves, removes this checkout's earlier base tree, then checks COMMIT
        out as a detached worktree in a new temporary directory, locked with this
        checkout's BASE_TREE_REASON, and prints its path
    design_check.py base-tree remove
        removes every worktree locked with this checkout's BASE_TREE_REASON, `ok` whether
        or not there was one; another checkout's base tree is left alone. It runs no
        `git worktree prune`, which would clear the stale entries of every other worktree
    design_check.py --self-test     runs every case below; exit 0 only if each one matches

A failed check prints `INVALID: <what>` to standard error, naming every key that fails or
the title, and exits 1; exit 2 is usage. Whether either path is gitignored is the skill's
check, not this script's.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "gates", "scripts"))
from project_rules import (FILE_NAME_MAX, NO_LETTER, OptionalKey, RequiredKey,  # noqa: E402
                           check_repo_path, cli_case, design_dirs, error_message,
                           isolated_git_environment, read_config, read_keys, report,
                           result_or_message, run_check, run_git, slug_of, text_input,
                           unset_keys, write_scratch)

# adr_dir may be left unset: gates/design-exit.md fails an unset adr_dir only for a design with
# a costly-to-reverse choice, which the gate, not this check, can see.
KEYS = (RequiredKey("design_dir"), OptionalKey("adr_dir", None))


def check_dirs(config):
    """"ok", with a note per optional key left unset, when every set key passes
    check_repo_path, design_dir is set, and design_dirs finds two directories, the rule
    design-read applies; otherwise ValueError naming each problem."""
    read_keys(config, KEYS)
    design_dirs(config)
    unset = unset_keys(config, KEYS)
    return "\t".join(["ok", *(f"{declared.key} not configured" for declared in KEYS
                              if declared.key in unset)])


# The longest name the skill builds from a slug is its ADR ignore check's `0000-<slug>.md`;
# the branch's lock file, `<slug>.lock`, is shorter.
SLUG_MAX = FILE_NAME_MAX - len("0000-") - len(".md")
SLUG_CASES = [
    ("fitted to the design's limit", "d" * 300, "d" * 247),
    ("no letter", "日本語", NO_LETTER.format("日本語")),
]


DESIGN_DIR_UNSET = "design_dir is absent, none, blank, or a placeholder"


def expected_message(config, keys):
    """What check_dirs should give, built apart from read_keys: keys itself when a string, the
    result; otherwise, in key order, the unset message for "design_dir unset" and
    check_repo_path's error for each other named key, `None` for one it accepts, so a wrong
    fixture fails its case rather than the self-test."""
    if isinstance(keys, str):
        return keys
    return "; ".join(DESIGN_DIR_UNSET if key == "design_dir unset" else
                     str(error_message(lambda key=key: check_repo_path(key, config.get(key))))
                     for key in ("design_dir unset", "design_dir", "adr_dir") if key in keys)


BASE_TREE_REASON = "design-feature base tree {}"


def base_tree_reason():
    """The lock reason naming the checkout this command runs in by a digest of its own git
    directory, as the skill's Step 6 state directory is per checkout: each checkout runs one
    design at a time, so a tree with its reason is its own, live or left by a killed run, and
    a tree another checkout's run is reading is never its to remove. A digest, not the path,
    so the reason is plain ASCII however the path is spelled."""
    git_dir = run_git(".", "rev-parse", "--absolute-git-dir").strip()
    return BASE_TREE_REASON.format(hashlib.sha256(git_dir.encode("utf8", "surrogateescape"))
                                   .hexdigest()[:16])


def worktrees(root=".", environment=None):
    """(path, lock reason or None) for every worktree git lists, the main one first, read
    from `--porcelain -z`, whose fields git never quotes: without -z a path or reason holding
    a non-ASCII character, a quote, or a backslash is C-quoted and matches nothing."""
    records, path, reason = [], None, None
    fields = run_git(root, "worktree", "list", "--porcelain", "-z",
                     environment=environment).split("\0")
    for field in fields + [""]:
        if field.startswith("worktree "):
            path, reason = field[len("worktree "):], None
        elif field == "locked" or field.startswith("locked "):
            reason = field[len("locked "):]
        elif field == "" and path is not None:
            records.append((path, reason))
            path = None
    return records


def base_trees():
    """The path of every worktree git lists as locked with this checkout's reason, whether
    or not its directory is still there."""
    owned = base_tree_reason()
    return [path for path, reason in worktrees() if reason == owned]


def base_tree_remove():
    """"ok" once git lists no base tree of this checkout: each is removed, its directory with
    it. `--force` twice removes a locked tree and one holding changes; no other worktree is
    touched."""
    for tree in base_trees():
        run_git(".", "worktree", "remove", "--force", "--force", tree)
    return "ok"


def base_tree_add(commit):
    """The path of a new detached worktree at commit, in a new temporary directory, once
    commit resolves and this checkout's earlier tree is removed. git records it locked with
    base_tree_reason, so a later remove finds it from `git worktree list` alone, even after a
    killed run, and `git worktree prune` leaves its entry for that remove."""
    try:
        sha = run_git(".", "rev-parse", "--verify", "--end-of-options",
                      f"{commit}^{{commit}}").strip()
    except ValueError as error:
        raise ValueError(f"{commit!r} is not a commit: {error}") from error
    base_tree_remove()
    tree = os.path.realpath(tempfile.mkdtemp(prefix="design-feature-base-"))
    try:
        run_git(".", "worktree", "add", "--detach", "--lock", "--reason", base_tree_reason(),
                tree, sha)
    except ValueError:
        shutil.rmtree(tree, ignore_errors=True)
        raise
    return tree


def git_in(repo, *arguments):
    """git's stdout in a self-test's scratch repository, with an isolated environment."""
    return run_git(repo, *arguments, environment=isolated_git_environment()).strip()


def base_tree_cases(script, directory):
    """base-tree run as the skill runs it, in a scratch repository with one commit and two
    worktrees of the user's own, one live and one whose directory is gone."""
    # A quote and a non-ASCII letter in every path, which git C-quotes outside -z.
    directory = os.path.join(directory, 'jos\u00e9 "q"')
    repo = os.path.realpath(os.path.join(directory, "repo"))
    os.makedirs(repo)
    git_in(repo, "init", "-q", "--template=")
    git_in(repo, "commit", "-q", "--allow-empty", "-m", "base")
    commit = git_in(repo, "rev-parse", "HEAD")
    own, stale = (os.path.realpath(os.path.join(directory, name)) for name in ("own", "stale"))
    git_in(repo, "worktree", "add", "-q", "--detach", own)
    git_in(repo, "worktree", "add", "-q", "--detach", stale)
    shutil.rmtree(stale)
    options = {"cwd": repo, "env": isolated_git_environment()}

    def base_tree_reason_of(checkout):
        digest = hashlib.sha256(os.path.join(checkout, ".git").encode("utf8")).hexdigest()
        return BASE_TREE_REASON.format(digest[:16])

    def run(*arguments, checkout=repo):
        return subprocess.run([sys.executable, script, "base-tree", *arguments],
                              capture_output=True, text=True, check=False,
                              **{**options, "cwd": checkout})

    def lock_of(tree):
        return next((reason for path, reason in worktrees(repo, isolated_git_environment())
                     if os.path.realpath(path) == tree), None)

    def listed():
        return sorted(os.path.realpath(path)
                      for path, _ in worktrees(repo, isolated_git_environment()))

    users = sorted([repo, own, stale])
    failures = 0
    first = run("add", "HEAD").stdout.strip()
    failures += report("base-tree", "add checks the commit out, detached and locked",
                       (listed() == sorted(users + [first]), git_in(first, "rev-parse", "HEAD"),
                        git_in(first, "branch", "--show-current"), lock_of(first)),
                       (True, commit, "", base_tree_reason_of(repo)))
    second = run("add", commit).stdout.strip()
    failures += report("base-tree", "add over a leftover removes the earlier tree first",
                       (listed() == sorted(users + [second]), os.path.exists(first),
                        second != first), (True, False, True))
    failures += report("base-tree", "remove leaves only the user's worktrees",
                       (run("remove").stdout.strip(), listed() == users, os.path.exists(second)),
                       ("ok", True, False))
    failures += report("base-tree", "remove with no tree is ok",
                       (run("remove").stdout.strip(), listed() == users), ("ok", True))
    gone = run("add", "HEAD").stdout.strip()
    shutil.rmtree(gone or os.path.join(directory, "missing"), ignore_errors=True)
    git_in(repo, "worktree", "prune")
    failures += report("base-tree", "remove after its directory was deleted and a prune ran",
                       (run("remove").returncode, listed()), (0, sorted([repo, own])))
    users = sorted([repo, own])
    held = run("add", "HEAD").stdout.strip()
    with open(os.path.join(held, "dirty"), "w", encoding="utf8") as handle:
        handle.write("untracked\n")
    failures += report("base-tree", "remove clears a tree holding an untracked file",
                       (run("remove").returncode, listed() == users, os.path.exists(held)),
                       (0, True, False))
    kept = run("add", "HEAD").stdout.strip()
    bad = run("add", "no-such-commit")
    failures += report("base-tree", "a bad commit is INVALID and removes nothing",
                       (bad.stderr.strip()[:42], bad.returncode,
                        listed() == sorted(users + [kept])),
                       ("INVALID: 'no-such-commit' is not a commit:", 1, True))
    theirs = run("add", "HEAD", checkout=own).stdout.strip()
    failures += report("base-tree", "a run in another checkout leaves this one's tree",
                       (listed() == sorted(users + [kept, theirs]), os.path.isdir(kept)),
                       (True, True))
    failures += report("base-tree", "remove in one checkout leaves the other's tree",
                       (run("remove").stdout.strip(), listed() == sorted(users + [theirs])),
                       ("ok", True))
    run("remove", checkout=own)
    git_in(repo, "worktree", "lock", "--reason", "the user's own", own)
    run("add", "HEAD")
    failures += report("base-tree", "remove leaves the user's locked worktree alone",
                       (run("remove").stdout.strip(), listed() == users, os.path.isdir(own)),
                       ("ok", True, True))
    failures += cli_case(script, "base-tree without a subcommand is usage", ["base-tree"], "", 2,
                         **options)
    return failures


VALID = {"design_dir": "docs/design", "adr_dir": "docs/adr"}
UNSET = "ok\tadr_dir not configured"
BOTH_FAILING = {"design_dir": "none", "adr_dir": "../adr"}
BOTH_FAILING_KEYS = ["design_dir unset", "adr_dir"]

DIRS_CASES = [
    ("both valid", VALID, "ok"),
    ("trailing slashes", {"design_dir": "docs/design/", "adr_dir": "docs/adr/"}, "ok"),
    ("design_dir none", {**VALID, "design_dir": "none"}, ["design_dir unset"]),
    ("design_dir a placeholder", {**VALID, "design_dir": "<directory>"}, ["design_dir unset"]),
    ("design_dir absolute", {**VALID, "design_dir": "/docs/design"}, ["design_dir"]),
    ("design_dir a leading dot", {**VALID, "design_dir": ".design"}, ["design_dir"]),
    ("design_dir inside .git", {**VALID, "design_dir": "x/.git"}, ["design_dir"]),
    ("design_dir inside .GIT", {**VALID, "design_dir": "x/.GIT"}, ["design_dir"]),
    ("design_dir a nested .git", {**VALID, "design_dir": "docs/.git/design"}, ["design_dir"]),
    ("adr_dir a mixed-case .Git", {**VALID, "adr_dir": "x/.Git/hooks"}, ["adr_dir"]),
    ("adr_dir ending in .git", {**VALID, "adr_dir": "docs/.git"}, ["adr_dir"]),
    ("adr_dir a .git with a trailing dot", {**VALID, "adr_dir": "docs/.git."}, ["adr_dir"]),
    ("adr_dir a .git with trailing dots", {**VALID, "adr_dir": "docs/.GIT.."}, ["adr_dir"]),
    ("a .git-prefixed name is not .git", {**VALID, "adr_dir": "docs/.github"}, "ok"),
    ("design_dir not a string", {**VALID, "design_dir": 5}, ["design_dir"]),
    ("design_dir absent", {"adr_dir": "docs/adr"}, ["design_dir unset"]),
    ("adr_dir absent", {"design_dir": "docs/design"}, UNSET),
    ("adr_dir none", {**VALID, "adr_dir": "None"}, UNSET),
    ("adr_dir blank", {**VALID, "adr_dir": " "}, UNSET),
    ("adr_dir a placeholder", {**VALID, "adr_dir": "<directory>"}, UNSET),
    ("adr_dir absolute", {**VALID, "adr_dir": "/docs/adr"}, ["adr_dir"]),
    ("adr_dir not a string", {**VALID, "adr_dir": ["docs/adr"]}, ["adr_dir"]),
    ("adr_dir a list holding a placeholder", {**VALID, "adr_dir": ["<directory>", "docs/adr"]},
     ["adr_dir"]),
    ("adr_dir outside the repository", {**VALID, "adr_dir": "docs/../../adr"}, ["adr_dir"]),
    ("adr_dir a shell metacharacter", {**VALID, "adr_dir": "docs/adr;rm"}, ["adr_dir"]),
    ("both failing", BOTH_FAILING, BOTH_FAILING_KEYS),
    ("design_dir unset with adr_dir unset", {}, ["design_dir unset"]),
    ("one directory for designs and ADRs", {"design_dir": "docs/d", "adr_dir": "docs/d/"},
     "adr_dir and design_dir name one directory, so no read can tell an ADR from a design"),
]


def self_test():
    failures = 0
    for name, config, keys in DIRS_CASES:
        failures += report("dirs", name,
                           result_or_message(lambda: check_dirs(config)),
                           expected_message(config, keys))
    for name, title, expected in SLUG_CASES:
        failures += report("slug", name, result_or_message(lambda: slug_of(title, SLUG_MAX)),
                           expected)
    script = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as directory:
        configs = {}
        for name, config in [("valid", VALID), ("design_dir none", {**VALID, "design_dir": "none"}),
                             ("adr_dir absent", {"design_dir": "docs/design"}),
                             ("adr_dir absolute", {**VALID, "adr_dir": "/docs/adr"}),
                             ("both failing", BOTH_FAILING)]:
            configs[name] = write_scratch(directory, config, f"{len(configs)}.json")
        unreadable = os.path.join(directory, "missing.json")
        for case in [
                ("dirs ok", ["dirs", "--config", configs["valid"]], "ok", 0),
                ("design_dir none", ["dirs", "--config", configs["design_dir none"]],
                 "INVALID: design_dir ", 1),
                ("adr_dir absent", ["dirs", "--config", configs["adr_dir absent"]], UNSET, 0),
                ("adr_dir absolute", ["dirs", "--config", configs["adr_dir absolute"]],
                 "INVALID: adr_dir ", 1),
                ("both failing", ["dirs", "--config", configs["both failing"]],
                 "INVALID: " + expected_message(BOTH_FAILING, BOTH_FAILING_KEYS), 1),
                ("an unreadable config", ["dirs", "--config", unreadable], "INVALID:", 1),
                ("dirs without --config is usage", ["dirs"], "", 2),
                ("slug of no letter", ["slug", "--title", "日本語"], "INVALID: title ", 1),
                ("no subcommand is usage", [], "", 2)]:
            failures += cli_case(script, *case)
        failures += cli_case(script, "slug", ["slug", "--title", "Add a design-feature skill"],
                             "add-a-design-feature-skill", 0, exact=True)
        failures += cli_case(script, "slug reads the title from stdin", ["slug"], "rob-s-design",
                             0, input="Rob's design\n", exact=True)
        failures += base_tree_cases(script, directory)
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("dirs").add_argument("--config", required=True)
    commands.add_parser("slug").add_argument("--title")
    base_tree = commands.add_parser("base-tree").add_subparsers(dest="action", required=True)
    base_tree.add_parser("add").add_argument("commit")
    base_tree.add_parser("remove")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return run_check(parser, {"dirs": lambda: check_dirs(read_config(args.config)),
                              "slug": lambda: slug_of(text_input(args.title), SLUG_MAX),
                              "base-tree": lambda: (base_tree_add(args.commit)
                                                    if args.action == "add"
                                                    else base_tree_remove())},
                     args.command)


if __name__ == "__main__":
    sys.exit(main())
