#!/usr/bin/env python3
"""Feature-design checks, so the skill settles none of them by eye. Standard library only.

Written for the design-feature skill to run before it writes a design.

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
from project_rules import (OptionalKey, RequiredKey, check_repo_path, cli_case,  # noqa: E402
                           collected_errors, error_message, read_config, read_keys, report,
                           run_check, shared_check)

# adr_dir may be left unset: gates/design-exit.md fails an unset adr_dir only for a design with
# a costly-to-reverse choice, which the gate, not this check, can see.
KEYS = (RequiredKey("design_dir", lambda value: check_repo_path("design_dir", value)),
        OptionalKey("adr_dir", shared_check("adr_dir"), None))


def check_dirs(config):
    """"ok", with a note per optional key left unset, when every set key passes
    check_repo_path and design_dir is set; otherwise ValueError naming each problem."""
    values = read_keys(config, KEYS)
    unset = [declared.key for declared in KEYS
             if isinstance(declared, OptionalKey) and values[declared.key] is None]
    return "\t".join(["ok", *(f"{key} not configured" for key in unset)])


DESIGN_DIR_UNSET = "design_dir is absent, none, blank, or a placeholder"


def expected_message(config, keys):
    """What check_dirs should give, built apart from read_keys: keys itself when a string, the
    result; otherwise, in key order, the unset message for "design_dir unset" and
    check_repo_path's error for each other named key."""
    if isinstance(keys, str):
        return keys
    return "; ".join(DESIGN_DIR_UNSET if key == "design_dir unset" else
                     error_message(lambda key=key: check_repo_path(key, config.get(key)))
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


def result_or_message(call):
    """The call's result, or the message of the ValueError it raises."""
    try:
        return call()
    except ValueError as error:
        return str(error)


def text(key):
    """A check that the key's value is text, naming the key."""
    def check(value):
        if not isinstance(value, str):
            raise ValueError(f"{key} is not text")
    return check


READ_KEYS_CASES = [
    ("a required key unset is named", {}, [RequiredKey("k", text("k"))],
     "k is absent, none, blank, or a placeholder"),
    ("a required key says who needs it", {"k": "none"},
     [RequiredKey("k", text("k"), needed_by="mobile")],
     "k is absent, none, blank, or a placeholder, and mobile needs it"),
    ("an optional key unset takes its default", {"k": "<k>"}, [OptionalKey("k", text("k"), 7)],
     {"k": 7}),
    ("a set key is checked", {"k": 5}, [OptionalKey("k", text("k"), 7)], "k is not text"),
    ("a template list reads as unset", {"k": ["<handle>"]},
     [OptionalKey("k", text("k"), 7, template_list=True)], {"k": 7}),
    ("any other list holding a placeholder is checked", {"k": ["<handle>"]},
     [OptionalKey("k", text("k"), 7)], "k is not text"),
    ("every problem is named", {"j": 5}, [RequiredKey("k", text("k")), RequiredKey("j", text("j"))],
     "k is absent, none, blank, or a placeholder; j is not text"),
    ("a required template list reads as unset", {"k": ["<os> <version>"]},
     [RequiredKey("k", text("k"), template_list=True)],
     "k is absent, none, blank, or a placeholder"),
]


def raise_empty():
    raise ValueError("")


def self_test():
    failures = 0
    for name, config, keys in DIRS_CASES:
        failures += report("dirs", name,
                           result_or_message(lambda: check_dirs(config)),
                           expected_message(config, keys))
    for name, config, keys, expected in READ_KEYS_CASES:
        failures += report("read_keys", name, result_or_message(lambda: read_keys(config, keys)),
                           expected)
    failures += report("collected_errors", "a ValueError with no message still counts",
                       collected_errors([raise_empty, lambda: None]), [""])
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
                 "INVALID: " + expected_message(BOTH_FAILING, BOTH_FAILING_KEYS), 1),
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
