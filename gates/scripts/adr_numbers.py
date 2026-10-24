#!/usr/bin/env python3
"""Whether any two decision records under `adr_dir` share a number. Standard library only.

Called by skills/ci-green/SKILL.md's merge step, the re-check gates/design-exit.md's
criterion 2 names, and by this repository's CI on its own `adr_dir`.

    adr_numbers.py [--config FILE] [--head REF]
        checks the `adr_dir` of HEAD, or of the --head commit, in the repository whose
        `.claude/project.json` FILE is (default: the current directory's)
    adr_numbers.py --against REF [--config FILE] [--head REF]
        checks the merge of the head into REF: REF's records, plus those the head added
        since their merge base, less those it deleted — what merging the branch would leave
    adr_numbers.py --self-test     runs every case below; exit 0 only if each one matches

A record is a file directly under `adr_dir` named `NNNN-<title>.md`, its number read as an
integer so `0003` and `003` collide. Against a ref, only a number one of the head's added
records shares counts. Prints `unique N`, or `duplicate N` and one `<number> <path>
<path>...` line per shared number; exit 0 only if unique. `adr_dir` unset
prints `adr_dir not configured` and exits 0, since nothing can collide. Exit 2 is no
answer: an unreadable project.json, an invalid `adr_dir`, or a git failure.
"""
import argparse
import collections
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from project_rules import (check_repo_path, error_message, git_subcommand,  # noqa: E402
                           is_unset_scalar, run_git, isolated_git_environment, read_config,
                           report)

RECORD = re.compile(r"^(\d+)-[^/]+\.md$")
GIT_ENVIRONMENT = None  # the self-test's isolated environment; None is the caller's


def git(root, *arguments):
    return run_git(root, *arguments, environment=GIT_ENVIRONMENT)


def records(root, ref, adr_dir):
    """The record paths directly under adr_dir at ref, since ls-tree without -r lists no
    subdirectory's files; none when ref has no adr_dir."""
    listed = git(root, "ls-tree", "--name-only", "-z", ref, "--", adr_dir + "/")
    return {path for path in listed.split("\0") if RECORD.match(os.path.basename(path))}


def merged_records(root, adr_dir, against, head_ref="HEAD"):
    """(records, added): the head's records alone, or what merging the head into against
    would leave; added is what the head added since the merge base, or None alone."""
    for ref in (head_ref, against) if against else (head_ref,):
        if ref.startswith("-"):
            raise ValueError(f"{ref!r} is not a ref")
        git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    head = records(root, head_ref, adr_dir)
    if against is None:
        return head, None
    base = records(root, git(root, "merge-base", against, head_ref).strip(), adr_dir)
    return (records(root, against, adr_dir) | (head - base)) - (base - head), head - base


def duplicates(paths):
    """{number: sorted paths} for each number more than one path holds."""
    by_number = collections.defaultdict(list)
    for path in paths:
        by_number[int(RECORD.match(os.path.basename(path)).group(1))].append(path)
    return {number: sorted(held) for number, held in by_number.items() if len(held) > 1}


def adr_dir_of(config):
    """adr_dir from project.json, or None when unset; ValueError when invalid."""
    value = read_config(config).get("adr_dir")
    if is_unset_scalar(value):
        return None
    check_repo_path("adr_dir", value)
    return os.path.normpath(value)


def check(config, against=None, head_ref="HEAD"):
    """(exit code, printed lines) for the CLI. The repository is the one holding config, at
    <root>/.claude/project.json."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(config)))
    adr_dir = adr_dir_of(config)
    if adr_dir is None:
        return 0, ["adr_dir not configured"]
    paths, added = merged_records(root, adr_dir, against, head_ref)
    # Against a ref, only a number one of the head's own records shares is the branch's to
    # fix; a duplicate already on the ref fails that ref's own check, not every branch.
    every = duplicates(paths)
    shared = {number: held for number, held in every.items()
              if added is None or added.intersection(held)}
    skipped = [f"already on {against}: {number:04d} {' '.join(held)}"
               for number, held in sorted(every.items()) if number not in shared]
    if not shared:
        return 0, [f"unique {len(paths)}" if not skipped else
                   f"unique to the head, {len(skipped)} already duplicated on {against}"] + skipped
    return 1, [f"duplicate {len(shared)}"] + [f"{number:04d} {' '.join(held)}"
                                             for number, held in sorted(shared.items())] + skipped


def self_test():
    global GIT_ENVIRONMENT
    failures = 0
    for name, arguments, expected in [
            ("a bare subcommand", ["log"], "log"),
            ("past -c and -C and their values", ["-C", ".", "-c", "k.v=1", "log"], "log"),
            ("past a separated --git-dir value", ["--git-dir", "/x", "log"], "log"),
            ("past a joined --git-dir value", ["--git-dir=/x", "log"], "log"),
            ("a trailing -c with no value", ["-c"], None),
            ("options only", ["--version"], None),
            ("no arguments", [], None)]:
        failures += report("git_subcommand", name, git_subcommand(arguments), expected)
    GIT_ENVIRONMENT = isolated_git_environment(GIT_AUTHOR_NAME="override")
    failures += report("isolated_git_environment", "an override beats the defaults",
                       GIT_ENVIRONMENT["GIT_AUTHOR_NAME"], "override")
    GIT_ENVIRONMENT = isolated_git_environment()
    with tempfile.TemporaryDirectory() as root:
        def write(path, text="x\n"):
            full = os.path.join(root, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf8") as handle:
                handle.write(text)

        def commit(message):
            git(root, "add", "-A")
            git(root, "commit", "--quiet", "--allow-empty", "-m", message)

        def branch(name, start="main"):
            git(root, "checkout", "--quiet", "-B", name, start)

        def run(against=None, head_ref="HEAD"):
            try:
                return check(config, against, head_ref)[0]
            except ValueError:
                return 2

        config = os.path.join(root, ".claude", "project.json")
        git(root, "init", "--quiet", "--initial-branch=main")
        write(".claude/project.json", '{"adr_dir": "none"}\n')
        write("docs/adr/0001-a.md")
        commit("unset")
        failures += report("check", "adr_dir unset", check(config), (0, ["adr_dir not configured"]))
        write(".claude/project.json", '{"adr_dir": "../outside"}\n')
        commit("invalid")
        failures += report("check", "an adr_dir outside the repository", run(), 2)
        write(".claude/project.json", '{"adr_dir": ["<directory>", "docs/adr"]}\n')
        failures += report("check", "an adr_dir list holding a placeholder", run(), 2)
        write(".claude/project.json", '{"adr_dir": "docs/adr"}\n')
        write("docs/adr/README.md")
        write("docs/adr/template.md")
        write("docs/adr/0002-b.md")
        commit("main")
        failures += report("check", "non-record files are ignored", check(config), (0, ["unique 2"]))

        branch("padding")
        write("docs/adr/002-c.md")
        commit("padding")
        failures += report("check", "numbers differing only in zero padding", run(), 1)

        branch("nested")
        write("docs/adr/old/0001-z.md")
        commit("nested")
        failures += report("check", "a file in a subdirectory is not a record", run(), 0)

        branch("design")
        write("docs/adr/0003-d.md")
        commit("design")
        branch("rival")
        write("docs/adr/0003-e.md")
        commit("rival")
        failures += report("check", "two designs merged with one number", run("design"), 1)
        failures += report("check", "HEAD alone, before the rival merges", run(), 0)
        failures += report("cli output", "the colliding paths are named", check(config, "design")[1],
                           ["duplicate 1", "0003 docs/adr/0003-d.md docs/adr/0003-e.md"])
        branch("follow", "design")
        write("docs/adr/0004-g.md")
        commit("follow")
        failures += report("check", "the same record on both sides", run("design"), 0)

        branch("rename", "design")
        git(root, "mv", "docs/adr/0003-d.md", "docs/adr/0003-renamed.md")
        commit("rename")
        failures += report("check", "a record renamed from REF's path", run("design"), 0)

        branch("refilled")
        os.remove(os.path.join(root, "docs/adr/0002-b.md"))
        write("docs/adr/0002-f.md")
        commit("refilled")
        branch("untouched")
        write("docs/adr/0005-u.md")
        commit("untouched")
        failures += report("check", "a record REF renumbered and refilled, the branch untouched",
                           run("refilled"), 0)
        branch("refilled-here")
        os.remove(os.path.join(root, "docs/adr/0002-b.md"))
        write("docs/adr/0002-h.md")
        commit("refilled-here")
        failures += report("check", "a record the branch deleted and refilled, REF still holding it",
                           run("main"), 0)
        failures += report("check", "--head names the commit checked, not HEAD",
                           run("design", head_ref="rival"), 1)
        failures += report("check", "a --head git cannot resolve", run(head_ref="no-such-ref"), 2)

        failures += report("check", "a REF git cannot resolve", run("no-such-ref"), 2)
        git(root, "checkout", "--quiet", "rival")
        failures += report("check", "a ref read as an option", run("--output=x"), 2)
        failures += report("run_git", "a failure names the subcommand past -c and -C",
                           error_message(lambda: git(root, "-C", ".", "-c", "k.v=1", "log",
                                                     "no-such-ref")).split(" failed")[0],
                           "git log")
        failures += report("run_git", "bytes when text is False",
                           run_git(root, "rev-parse", "--git-dir", environment=GIT_ENVIRONMENT,
                                   text=False), b".git\n")
        branch("adds-nothing", "padding")
        write("notes.md")
        commit("adds-nothing")
        failures += report("check", "a duplicate already on REF, the branch adding none",
                           run("padding"), 0)
        branch("adds-one", "padding")
        write("docs/adr/0001-m.md")
        commit("adds-one")
        failures += report("cli output", "only the head's number fails, REF's is named apart",
                           check(config, "padding"),
                           (1, ["duplicate 1", "0001 docs/adr/0001-a.md docs/adr/0001-m.md",
                                "already on padding: 0002 docs/adr/0002-b.md docs/adr/002-c.md"]))

        def cli(*arguments):
            completed = subprocess.run([sys.executable, os.path.abspath(__file__), "--config",
                                        config, *arguments], capture_output=True, text=True,
                                       check=False, env=GIT_ENVIRONMENT)
            return completed.returncode, completed.stderr.startswith("NO ANSWER:")

        failures += report("cli", "a collision exits 1", cli("--against", "design"), (1, False))
        missing = subprocess.run([sys.executable, os.path.abspath(__file__), "--config",
                                  os.path.join(root, "absent.json")], capture_output=True,
                                 text=True, check=False, env=GIT_ENVIRONMENT)
        failures += report("cli", "a missing --config exits 2", missing.returncode, 2)
        failures += report("cli", "a git failure exits 2, never 1", cli("--against", "no-such-ref"),
                           (2, True))
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--config", default=os.path.join(".claude", "project.json"))
    parser.add_argument("--against", metavar="REF")
    parser.add_argument("--head", metavar="REF", default="HEAD")
    args = parser.parse_args()
    if args.self_test:
        return 1 if self_test() else 0
    try:
        code, lines = check(args.config, args.against, args.head)
    except (ValueError, OSError) as error:
        print(f"NO ANSWER: {error}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
