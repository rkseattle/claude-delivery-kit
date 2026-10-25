#!/usr/bin/env python3
"""Feature-design checks, so the skill settles none of them by eye. Standard library only.

Written for the design-feature skill to run before it writes a design.

    design_check.py dirs --config PATH
        `ok` when design_dir and adr_dir are each a relative path inside the repository, as
        release_dir must be; `ok\tadr_dir not configured` when adr_dir is unset, which
        gates/design-exit.md fails only for a design with a costly-to-reverse choice
    design_check.py slug [--title TITLE]
        the design's <slug> for the title, or standard input: project_rules.slug_of fitted
        to SLUG_MAX; INVALID when no letter or digit is left
    design_check.py --self-test     runs every case below; exit 0 only if each one matches

A failed check prints `INVALID: <what>` to standard error, naming every key that fails or
the title, and exits 1; exit 2 is usage. Whether either path is gitignored is the skill's
check, not this script's.
"""
import argparse
import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "gates", "scripts"))
from project_rules import (FILE_NAME_MAX, NO_LETTER, OptionalKey, RequiredKey,  # noqa: E402
                           check_repo_path, cli_case, error_message, read_config, read_keys,
                           report, result_or_message, run_check, slug_of, text_input, unset_keys,
                           write_scratch)

# adr_dir may be left unset: gates/design-exit.md fails an unset adr_dir only for a design with
# a costly-to-reverse choice, which the gate, not this check, can see.
KEYS = (RequiredKey("design_dir"), OptionalKey("adr_dir", None))


def check_dirs(config):
    """"ok", with a note per optional key left unset, when every set key passes
    check_repo_path and design_dir is set; otherwise ValueError naming each problem."""
    read_keys(config, KEYS)
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
    ("design_dir inside .git", {**VALID, "design_dir": "docs/../.git"}, ["design_dir"]),
    ("design_dir inside .GIT", {**VALID, "design_dir": "docs/../.GIT"}, ["design_dir"]),
    ("design_dir a nested .git", {**VALID, "design_dir": "docs/.git/design"}, ["design_dir"]),
    ("adr_dir a mixed-case .Git", {**VALID, "adr_dir": "x/../.Git/hooks"}, ["adr_dir"]),
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
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("dirs").add_argument("--config", required=True)
    commands.add_parser("slug").add_argument("--title")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return run_check(parser, {"dirs": lambda: check_dirs(read_config(args.config)),
                              "slug": lambda: slug_of(text_input(args.title), SLUG_MAX)},
                     args.command)


if __name__ == "__main__":
    sys.exit(main())
