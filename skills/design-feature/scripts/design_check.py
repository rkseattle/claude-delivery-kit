#!/usr/bin/env python3
"""Feature-design checks, so the skill settles none of them by eye. Standard library only.

Written for the design-feature skill to run before it writes a design; review-tickets runs
its base-tree too, as its own owner, to review a recorded design.

    design_check.py dirs --config PATH
        `ok` when design_dir and adr_dir are each a relative path inside the repository, as
        release_dir must be, and not one directory, as project_rules.design_dirs rules;
        `ok\tadr_dir not configured` when adr_dir is unset, which
        gates/design-exit.md fails only for a design with a costly-to-reverse choice
    design_check.py slug [--title TITLE]
        the design's <slug> for the title, or standard input: project_rules.slug_of fitted
        to SLUG_MAX; INVALID when no letter or digit is left
    design_check.py base-tree add COMMIT --config PATH [--new-branch NAME] [--owner OWNER]
        once COMMIT resolves, removes OWNER's stale base trees of the checkout PATH belongs
        to, then checks COMMIT out as a worktree in a new directory inside its git directory,
        detached or on NAME, created there, locked with that checkout's BASE_TREE_REASON for
        OWNER and the time it was added, and prints the tree's path
    design_check.py base-tree remove --config PATH [--owner OWNER] [--tree TREE]
        with TREE, removes that tree, the path add printed, `ok` too once git lists it no
        more; INVALID for a worktree that is not OWNER's base tree of this checkout. Without
        TREE, removes only OWNER's stale trees: those whose directory is gone, older than
        STALE_AFTER, or locked by a release that recorded none, timed by its lock file. With
        --if-stale, TREE is removed only once stale, INVALID while another session may hold
        it. A session holding a tree past STALE_AFTER can lose it to another session. A live tree of another
        session, another checkout's, or another owner's is left alone. It runs no `git
        worktree prune`, which would clear the stale entries of every other worktree. OWNER
        is one of OWNERS, the skill whose tree it is, design-feature by default
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
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "gates", "scripts"))
from project_rules import (FILE_NAME_MAX, NO_LETTER, OptionalKey, RequiredKey,  # noqa: E402
                           check_repo_path, cli_case, design_dirs, error_message,
                           isolated_git_environment, project_root, read_config, read_keys,
                           report,
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


BASE_TREE_REASON = "{} base tree {}"
# A tree is another session's, live, until this old, as git gc takes over a gc.pid lock
# whose process it cannot see after 12 hours; a design run removes its tree before each stop.
# The known limit: a session holding one tree longer than this can lose it to another's run.
STALE_AFTER = 12 * 60 * 60
# What add appends to base_tree_reason: the epoch seconds it added the tree at.
SINCE = " since {}"


def added_at(reason, owned):
    """The epoch seconds a lock reason records after owned, base_tree_reason's prefix, as
    add writes it with SINCE; None for the bare prefix an earlier release wrote, and False
    for any other reason, which is no tree of owned's."""
    if reason == owned:
        return None
    since = (reason or "").removeprefix(owned + SINCE.format(""))
    return int(since) if since != reason and since.isdigit() else False
# The skills that keep a base tree, each its own per checkout, so one never removes another's.
OWNERS = ("design-feature", "review-tickets")


def base_tree_reason(root, owner=OWNERS[0]):
    """The lock reason naming owner, the skill whose tree it is, and the checkout at root,
    the project folder, by a digest of its git directory, which add follows with ` since
    <epoch seconds>`. Two sessions of one owner may run in one checkout, so a tree with this
    reason is removed by the path add printed it at, or once stale_tree finds it stale; a
    tree another checkout's or another owner's run is reading is never its to remove. Read
    from root, not the shell's directory, so a command run from inside the tree still names
    its checkout. A digest, not the path, so the reason is plain ASCII however the path is
    spelled."""
    git_dir = run_git(root, "rev-parse", "--absolute-git-dir").strip()
    digest = hashlib.sha256(git_dir.encode("utf8", "surrogateescape")).hexdigest()
    return BASE_TREE_REASON.format(owner, digest[:16])


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


def base_trees(root, owner=OWNERS[0]):
    """(path, epoch seconds it was added or None) for every worktree git lists as locked
    with root's reason for owner, whether or not its directory is still there; None for a
    tree locked by a release that recorded no time."""
    owned = base_tree_reason(root, owner)
    return [(path, lock_time(root, path) if since is None else since)
            for path, reason in worktrees(root)
            for since in [added_at(reason, owned)] if since is not False]


def lock_time(root, path):
    """When git locked the worktree at path, from the mtime of the `locked` file `git
    worktree lock` writes in its administrative directory, for a lock an earlier release
    wrote with no time; None when no such directory names path."""
    common = run_git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    admin = os.path.join(common, "worktrees")
    for entry in sorted(os.listdir(admin)) if os.path.isdir(admin) else []:
        try:
            with open(os.path.join(admin, entry, "gitdir"), encoding="utf8") as handle:
                listed = os.path.dirname(handle.read().strip())
            if os.path.realpath(listed) == os.path.realpath(path):
                return int(os.path.getmtime(os.path.join(admin, entry, "locked")))
        except OSError:
            continue
    return None


def stale_tree(path, since, now):
    """Whether no live session can be reading the tree: its directory is gone, it was added
    STALE_AFTER ago or more, or no time is known for its lock."""
    return since is None or not os.path.isdir(path) or now - since >= STALE_AFTER


def base_tree_remove(config, owner=OWNERS[0], tree=None, if_stale=False):
    """"ok" once git lists neither tree nor, without tree, any stale base tree of owner's in
    the checkout config belongs to: each is removed, its directory with it. `--force` twice
    removes a locked tree and one holding changes. ValueError for a tree git lists that is
    not owner's base tree of this checkout, so no other worktree, a live one of another
    session or another owner's included, is touched, and with if_stale for a tree that is not
    stale, which another session may still be using."""
    root = project_root(config)
    owned = base_trees(root, owner)
    now = time.time()
    if tree is None:
        targets = [path for path, since in owned if stale_tree(path, since, now)]
    else:
        real = os.path.realpath(tree)
        mine = {os.path.realpath(path): since for path, since in owned}
        if real in mine:
            if if_stale and not stale_tree(real, mine[real], now):
                raise ValueError(f"{tree!r} is live: another session may still be using it")
            targets = [real]
        elif real in {os.path.realpath(path) for path, _ in worktrees(root)}:
            raise ValueError(f"{tree!r} is not a {owner} base tree of this checkout")
        else:
            targets = []
    for path in targets:
        run_git(root, "worktree", "remove", "--force", "--force", path)
    return "ok"


def base_tree_add(commit, config, new_branch=None, owner=OWNERS[0]):
    """The path of a new worktree at commit, detached, or with new_branch created there and
    checked out, once commit resolves, new_branch is a branch name no branch holds yet, and
    owner's stale trees of the checkout config belongs to are removed. It is a new directory in
    that checkout's git directory, so the session reads it without leaving the project, and
    git status never shows it. The tree is the base exactly: nothing is written into it here.
    git records the tree locked with base_tree_reason, so a later
    remove finds it from `git worktree list` alone, even after a killed run, and `git
    worktree prune` leaves its entry for that remove. Removing the tree leaves new_branch and
    its commits."""
    root = project_root(config)
    try:
        sha = run_git(root, "rev-parse", "--verify", "--end-of-options",
                      f"{commit}^{{commit}}").strip()
    except ValueError as error:
        raise ValueError(f"{commit!r} is not a commit: {error}") from error
    if new_branch is not None:
        try:
            run_git(root, "check-ref-format", "--branch", new_branch)
        except ValueError as error:
            raise ValueError(f"{new_branch!r} is not a branch name: {error}") from error
        if run_git(root, "for-each-ref", "--format=%(refname)", f"refs/heads/{new_branch}"):
            raise ValueError(f"branch {new_branch!r} already exists")
    base_tree_remove(config, owner)
    git_dir = run_git(root, "rev-parse", "--absolute-git-dir").strip()
    tree = os.path.realpath(tempfile.mkdtemp(prefix=f"{owner}-base-", dir=git_dir))
    checkout = ["--detach"] if new_branch is None else ["-b", new_branch]
    try:
        run_git(root, "worktree", "add", *checkout, "--lock", "--reason",
                base_tree_reason(root, owner) + SINCE.format(int(time.time())), tree, sha)
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
    write_scratch(repo, {"design_dir": "docs/design"}, ".claude/project.json")
    git_in(repo, "add", ".claude/project.json")
    git_in(repo, "commit", "-q", "-m", "base")
    commit = git_in(repo, "rev-parse", "HEAD")
    own, stale = (os.path.realpath(os.path.join(directory, name)) for name in ("own", "stale"))
    git_in(repo, "worktree", "add", "-q", "--detach", own)
    git_in(repo, "worktree", "add", "-q", "--detach", stale)
    shutil.rmtree(stale)
    options = {"cwd": repo, "env": isolated_git_environment()}

    def base_tree_reason_of(checkout, owner=OWNERS[0]):
        digest = hashlib.sha256(os.path.join(checkout, ".git").encode("utf8")).hexdigest()
        return BASE_TREE_REASON.format(owner, digest[:16])

    def run(*arguments, checkout=repo, cwd=None):
        config = os.path.join(checkout, ".claude", "project.json")
        return subprocess.run([sys.executable, script, "base-tree", *arguments,
                               "--config", config], capture_output=True, text=True,
                              check=False, **{**options, "cwd": cwd or checkout})

    def lock_of(tree, owner=OWNERS[0]):
        reason = next((reason for path, reason in worktrees(repo, isolated_git_environment())
                       if os.path.realpath(path) == tree), None)
        owned = base_tree_reason_of(repo, owner)
        return owned if added_at(reason, owned) not in (None, False) else reason

    def relock(tree, reason):
        git_in(repo, "worktree", "unlock", tree)
        git_in(repo, "worktree", "lock", "--reason", reason, tree)

    def age(tree):
        reason = next(reason for path, reason in worktrees(repo, isolated_git_environment())
                      if os.path.realpath(path) == tree)
        relock(tree, reason.rpartition(SINCE.format(""))[0] + SINCE.format(0))

    def listed():
        return sorted(os.path.realpath(path)
                      for path, _ in worktrees(repo, isolated_git_environment()))

    users = sorted([repo, own, stale])
    failures = 0
    first = run("add", "HEAD").stdout.strip()
    pinned = hashlib.sha256(os.path.join(repo, ".git").encode("utf8")).hexdigest()[:16]
    failures += report("base-tree", "the default owner's lock reason is the released one",
                       base_tree_reason_of(repo), "design-feature base tree " + pinned)
    failures += report("base-tree", "add checks the commit out, detached and locked",
                       (listed() == sorted(users + [first]), git_in(first, "rev-parse", "HEAD"),
                        git_in(first, "branch", "--show-current"), lock_of(first)),
                       (True, commit, "", base_tree_reason_of(repo)))
    second = run("add", commit).stdout.strip()
    failures += report("base-tree", "add beside another session's live tree keeps it",
                       (listed() == sorted(users + [first, second]), os.path.isdir(first),
                        second != first), (True, True, True))
    failures += report("base-tree", "remove with no tree keeps live trees",
                       (run("remove").stdout.strip(), listed() == sorted(users + [first, second])),
                       ("ok", True))
    age(first)
    third = run("add", "HEAD").stdout.strip()
    failures += report("base-tree", "add removes a tree older than STALE_AFTER",
                       (os.path.exists(first), listed() == sorted(users + [second, third])),
                       (False, True))
    relock(third, base_tree_reason_of(repo))
    failures += report("base-tree", "remove keeps a fresh tree locked with no time, as 1.3 did",
                       (run("remove").stdout.strip(), os.path.isdir(third)), ("ok", True))
    admin = os.path.join(repo, ".git", "worktrees")
    for entry in os.listdir(admin):
        with open(os.path.join(admin, entry, "gitdir"), encoding="utf8") as handle:
            if os.path.realpath(os.path.dirname(handle.read().strip())) == third:
                os.utime(os.path.join(admin, entry, "locked"), (0, 0))
    failures += report("base-tree", "remove clears an old tree locked with no time",
                       (run("remove").stdout.strip(), listed() == sorted(users + [second])),
                       ("ok", True))
    live = run("remove", "--tree", second, "--if-stale")
    failures += report("base-tree", "remove --if-stale keeps a live tree another session holds",
                       (live.returncode, live.stderr.startswith("INVALID: "),
                        os.path.isdir(second)), (1, True, True))
    failures += report("base-tree", "remove --tree leaves only the user's worktrees",
                       (run("remove", "--tree", second).stdout.strip(), listed() == users,
                        os.path.exists(second)), ("ok", True, False))
    failures += report("base-tree", "remove --tree of a tree already gone is ok",
                       run("remove", "--tree", second).stdout.strip(), "ok")
    refused = run("remove", "--tree", own)
    failures += report("base-tree", "remove --tree refuses the user's own worktree",
                       (refused.returncode, refused.stderr.startswith("INVALID: "),
                        os.path.isdir(own)), (1, True, True))
    elsewhere = run("add", "HEAD", cwd=directory).stdout.strip()
    inside = run("remove", "--tree", elsewhere, cwd=elsewhere)
    failures += report("base-tree", "remove run from inside the tree removes it",
                       (inside.stdout.strip(), listed() == users, os.path.exists(elsewhere)),
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
                       (run("remove", "--tree", held).returncode, listed() == users, os.path.exists(held)),
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
    refused = run("remove", "--tree", theirs)
    failures += report("base-tree", "remove --tree refuses another checkout's tree",
                       (refused.returncode, os.path.isdir(theirs)), (1, True))
    failures += report("base-tree", "remove in one checkout leaves the other's tree",
                       (run("remove", "--tree", kept).stdout.strip(),
                        listed() == sorted(users + [theirs])), ("ok", True))
    run("remove", "--tree", theirs, checkout=own)
    git_in(repo, "worktree", "lock", "--reason", "the user's own", own)
    locked = run("add", "HEAD").stdout.strip()
    failures += report("base-tree", "remove leaves the user's locked worktree alone",
                       (run("remove", "--tree", locked).stdout.strip(), listed() == users,
                        os.path.isdir(own)), ("ok", True, True))
    git_dir = os.path.join(repo, ".git")
    branched = run("add", "HEAD", "--new-branch", "design/x").stdout.strip()
    failures += report("base-tree", "add --new-branch cuts the branch there, inside the git dir",
                       (git_in(branched, "branch", "--show-current"),
                        git_in(repo, "rev-parse", "design/x"),
                        os.path.dirname(branched) == git_dir, lock_of(branched)),
                       ("design/x", commit, True, base_tree_reason_of(repo)))
    git_in(branched, "commit", "-q", "--allow-empty", "-m", "design")
    tip = git_in(repo, "rev-parse", "design/x")
    failures += report("base-tree", "remove keeps the branch and its commit",
                       (run("remove", "--tree", branched).stdout.strip(), listed() == users,
                        git_in(repo, "rev-parse", "design/x"), tip != commit,
                        git_in(repo, "status", "--porcelain")), ("ok", True, tip, True, ""))
    taken = run("add", "HEAD", "--new-branch", "design/x")
    failures += report("base-tree", "an existing branch is INVALID and adds nothing",
                       (taken.stderr.strip(), taken.returncode, listed() == users),
                       ("INVALID: branch 'design/x' already exists", 1, True))
    malformed = run("add", "HEAD", "--new-branch", "a..b")
    failures += report("base-tree", "a malformed branch name is INVALID",
                       (malformed.stderr.strip()[:41], malformed.returncode),
                       ("INVALID: 'a..b' is not a branch name: git", 1))
    missing = subprocess.run([sys.executable, script, "base-tree", "add", "HEAD", "--config",
                              os.path.join(directory, "nowhere", ".claude", "project.json")],
                             capture_output=True, text=True, check=False, **options)
    failures += report("base-tree", "an unreadable --config is INVALID and adds nothing",
                       (missing.stderr.strip()[:8], missing.returncode, listed() == users),
                       ("INVALID:", 1, True))
    failures += cli_case(script, "base-tree without --config is usage",
                         ["base-tree", "remove"], "", 2, **options)
    failures += cli_case(script, "base-tree without a subcommand is usage", ["base-tree"], "", 2,
                         **options)
    ours = run("add", "HEAD").stdout.strip()
    age(ours)
    left = run("add", "HEAD", "--owner", "review-tickets").stdout.strip()
    age(left)
    review = run("add", "HEAD", "--owner", "review-tickets").stdout.strip()
    failures += report("base-tree", "an owner's add over its stale tree keeps another's",
                       (os.path.exists(left), os.path.isdir(ours), review != left),
                       (False, True, True))
    failures += report("base-tree", "another owner's add leaves the default owner's tree",
                       (listed() == sorted(users + [ours, review]), lock_of(review, "review-tickets"),
                        os.path.basename(review).startswith("review-tickets-base-")),
                       (True, base_tree_reason_of(repo, "review-tickets"), True))
    failures += report("base-tree", "the default owner's add and remove leave another owner's",
                       (run("remove", "--tree", ours).stdout.strip(),
                        listed() == sorted(users + [review])), ("ok", True))
    again = run("add", "HEAD").stdout.strip()
    crossed = run("remove", "--owner", "review-tickets", "--tree", again)
    failures += report("base-tree", "an owner's remove --tree refuses another owner's tree",
                       (crossed.returncode, os.path.isdir(again)), (1, True))
    failures += report("base-tree", "an owner's remove takes only its own tree",
                       (run("remove", "--owner", "review-tickets", "--tree", review).stdout.strip(),
                        listed() == sorted(users + [again]), os.path.exists(review)),
                       ("ok", True, False))
    run("remove", "--tree", again)
    elsewhere_review = run("add", "HEAD", "--owner", "review-tickets", checkout=own).stdout.strip()
    age(elsewhere_review)
    failures += report("base-tree", "remove --if-stale takes a stale tree",
                       (run("remove", "--owner", "review-tickets", "--tree", elsewhere_review,
                            "--if-stale", checkout=own).returncode,
                        os.path.isdir(elsewhere_review)), (0, False))
    elsewhere_review = run("add", "HEAD", "--owner", "review-tickets", checkout=own).stdout.strip()
    age(elsewhere_review)
    failures += report("base-tree", "an owner's remove leaves its tree in another checkout",
                       (run("remove", "--owner", "review-tickets").stdout.strip(),
                        os.path.isdir(elsewhere_review)), ("ok", True))
    run("remove", "--owner", "review-tickets", "--tree", elsewhere_review, checkout=own)
    failures += cli_case(script, "an unknown owner is usage",
                         ["base-tree", "remove", "--owner", "someone", "--config",
                          os.path.join(repo, ".claude", "project.json")], "", 2, **options)
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
    add = base_tree.add_parser("add")
    add.add_argument("commit")
    add.add_argument("--new-branch")
    add.add_argument("--config", required=True)
    add.add_argument("--owner", choices=OWNERS, default=OWNERS[0])
    remove = base_tree.add_parser("remove")
    remove.add_argument("--config", required=True)
    remove.add_argument("--owner", choices=OWNERS, default=OWNERS[0])
    remove.add_argument("--tree")
    remove.add_argument("--if-stale", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return run_check(parser, {"dirs": lambda: check_dirs(read_config(args.config)),
                              "slug": lambda: slug_of(text_input(args.title), SLUG_MAX),
                              "base-tree": lambda: (base_tree_add(args.commit, args.config,
                                                                  args.new_branch, args.owner)
                                                    if args.action == "add"
                                                    else base_tree_remove(args.config,
                                                                          args.owner,
                                                                          args.tree,
                                                                          args.if_stale))},
                     args.command)


if __name__ == "__main__":
    sys.exit(main())
