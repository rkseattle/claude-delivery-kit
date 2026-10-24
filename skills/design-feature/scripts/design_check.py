#!/usr/bin/env python3
"""Feature-design checks, so the skill settles none of them by eye. Standard library only.

For the design-feature skill, which runs `dirs` before it writes a design.

    design_check.py dirs --config PATH
        `ok` when design_dir and adr_dir are each a relative path inside the repository, as
        release_dir must be; `ok\tadr_dir not configured` when adr_dir is unset, which
        gates/design-exit.md fails only for a design with a costly-to-reverse choice
    design_check.py --self-test     runs every case below; exit 0 only if each one matches

A failed check prints `INVALID: <what>` to standard error, naming every key that fails, and
exits 1; exit 2 is usage. Whether either path is gitignored is the skill's check, not this
script's.
"""
import argparse
import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "gates", "scripts"))
from project_rules import (check_repo_path, cli_case, collected_errors,  # noqa: E402
                           error_message, is_unset, read_config, report, run_check)

KEYS = ("design_dir", "adr_dir")
# Keys for which unset is a valid setting, as gates/scripts/adr_numbers.py reads adr_dir.
OPTIONAL = ("adr_dir",)


def check_dirs(config):
    """"ok", with a note per optional key left unset, when every set key passes
    check_repo_path; otherwise ValueError naming each that fails."""
    unset = [key for key in OPTIONAL if is_unset(config.get(key))]
    errors = collected_errors(lambda key=key: check_repo_path(key, config.get(key))
                              for key in KEYS if key not in unset)
    if errors:
        raise ValueError("; ".join(errors))
    return "\t".join(["ok", *(f"{key} not configured" for key in unset)])


def expected_message(config, keys):
    """What check_dirs should give: keys itself when a string, the result; otherwise each
    named key's check_repo_path error, joined in KEYS order."""
    if isinstance(keys, str):
        return keys
    return "; ".join(error_message(lambda key=key: check_repo_path(key, config.get(key)))
                     for key in KEYS if key in keys)


VALID = {"design_dir": "docs/design", "adr_dir": "docs/adr"}
UNSET = "ok\tadr_dir not configured"
BOTH_FAILING = {"design_dir": "none", "adr_dir": "../adr"}

DIRS_CASES = [
    ("both valid", VALID, "ok"),
    ("trailing slashes", {"design_dir": "docs/design/", "adr_dir": "docs/adr/"}, "ok"),
    ("design_dir none", {**VALID, "design_dir": "none"}, ["design_dir"]),
    ("design_dir a placeholder", {**VALID, "design_dir": "<directory>"}, ["design_dir"]),
    ("design_dir absolute", {**VALID, "design_dir": "/docs/design"}, ["design_dir"]),
    ("design_dir a leading dot", {**VALID, "design_dir": ".design"}, ["design_dir"]),
    ("design_dir inside .git", {**VALID, "design_dir": "docs/../.git"}, ["design_dir"]),
    ("design_dir not a string", {**VALID, "design_dir": 5}, ["design_dir"]),
    ("design_dir absent", {"adr_dir": "docs/adr"}, ["design_dir"]),
    ("adr_dir absent", {"design_dir": "docs/design"}, UNSET),
    ("adr_dir none", {**VALID, "adr_dir": "None"}, UNSET),
    ("adr_dir blank", {**VALID, "adr_dir": " "}, UNSET),
    ("adr_dir a placeholder", {**VALID, "adr_dir": "<directory>"}, UNSET),
    ("adr_dir absolute", {**VALID, "adr_dir": "/docs/adr"}, ["adr_dir"]),
    ("adr_dir not a string", {**VALID, "adr_dir": ["docs/adr"]}, ["adr_dir"]),
    ("adr_dir outside the repository", {**VALID, "adr_dir": "docs/../../adr"}, ["adr_dir"]),
    ("adr_dir a shell metacharacter", {**VALID, "adr_dir": "docs/adr;rm"}, ["adr_dir"]),
    ("both failing", BOTH_FAILING, ["design_dir", "adr_dir"]),
    ("design_dir unset with adr_dir unset", {}, ["design_dir"]),
]


def self_test():
    failures = 0
    for name, config, keys in DIRS_CASES:
        failures += report("dirs", name,
                           error_message(lambda: check_dirs(config)) or check_dirs(config),
                           expected_message(config, keys))
    script = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as directory:
        configs = {}
        for name, config in [("valid", VALID), ("design_dir none", {**VALID, "design_dir": "none"}),
                             ("adr_dir absent", {"design_dir": "docs/design"}),
                             ("adr_dir absolute", {**VALID, "adr_dir": "/docs/adr"}),
                             ("both failing", BOTH_FAILING)]:
            configs[name] = os.path.join(directory, f"{len(configs)}.json")
            with open(configs[name], "w", encoding="utf-8") as handle:
                json.dump(config, handle)
        unreadable = os.path.join(directory, "missing.json")
        for case in [
                ("dirs ok", ["dirs", "--config", configs["valid"]], "ok", 0),
                ("design_dir none", ["dirs", "--config", configs["design_dir none"]],
                 "INVALID: design_dir ", 1),
                ("adr_dir absent", ["dirs", "--config", configs["adr_dir absent"]], UNSET, 0),
                ("adr_dir absolute", ["dirs", "--config", configs["adr_dir absolute"]],
                 "INVALID: adr_dir ", 1),
                ("both failing", ["dirs", "--config", configs["both failing"]],
                 "INVALID: " + expected_message(BOTH_FAILING, KEYS), 1),
                ("an unreadable config", ["dirs", "--config", unreadable], "INVALID:", 1),
                ("dirs without --config is usage", ["dirs"], "", 2),
                ("no subcommand is usage", [], "", 2)]:
            failures += cli_case(script, *case)
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("dirs").add_argument("--config", required=True)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return run_check(parser, {"dirs": lambda: check_dirs(read_config(args.config))},
                     args.command)


if __name__ == "__main__":
    sys.exit(main())
