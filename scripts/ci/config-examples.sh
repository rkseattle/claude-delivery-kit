#!/usr/bin/env bash
# No project.json key a kit script declares accepts the placeholder reference/project-json.md
# writes for it as a real setting: fed through project_rules' key_problems, each such
# placeholder in the example blocks reads as unset or is rejected, so a template copied
# unedited never configures anything. A key a script declares that the example blocks never show, at the top
# level or inside an object such as roles, fails too, and so does a declaring script that
# cannot be imported or holds no top-level declaration, so no declaration goes unchecked. A
# reference with no example block, or a tree with no declaration at all, fails rather than
# reading as clean.
#
# Every declaration is found by searching the kit's Python under gates/ and skills/ for
# `RequiredKey(` or `OptionalKey(` and importing each file holding one, then reading each
# declaration the module holds at its top level, in a tuple, list, or dict included; a
# self-test's fixture declarations live inside its functions, so they are not read. Only an
# example that is wholly a placeholder, or a list holding one, is judged: any other illustrates
# a real value, which the key may well accept, and a placeholder embedded in a longer string,
# such as a path, is not read as one.
# Usage: config-examples.sh [repo-root]
set -euo pipefail
root="$(cd "${1:-.}" && pwd)"
python3 - "$root" <<'PY'
import importlib.util
import json
import os
import re
import sys

sys.dont_write_bytecode = True
DECLARATION = re.compile(r"\b(?:RequiredKey|OptionalKey)\(")
JSON_BLOCK = re.compile(r"^```json\n(.*?)^```", re.M | re.S)


def example_values(root):
    """Each key the reference's example blocks show, and each role under roles, which a
    script reads from that object; raise ValueError when there is none to read."""
    path = os.path.join(root, "reference", "project-json.md")
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        blocks = [json.loads(block) for block in JSON_BLOCK.findall(text)]
    except (OSError, ValueError) as error:
        raise ValueError(f"NO REFERENCE: {path}: {error}")
    if not blocks or not all(isinstance(block, dict) for block in blocks):
        raise ValueError(f"NO REFERENCE: {path} holds no json block that is an object")
    values = {}
    for block in blocks:
        for key, value in block.items():
            if key in values and values[key] != value:
                raise ValueError(f"NO REFERENCE: {path} shows {key} twice, as {values[key]!r} "
                                 f"and {value!r}")
            values[key] = value
    roles = values.get("roles")
    values.update({role: entry for role, entry in (roles if isinstance(roles, dict) else {}).items()
                   if role not in values})
    return values


def declaring_files(root):
    found = []
    for top in ("gates", "skills"):
        for directory, subdirectories, files in os.walk(os.path.join(root, top)):
            subdirectories[:] = [d for d in subdirectories if d not in ("_vendor", "__pycache__")]
            for name in sorted(files):
                path = os.path.join(directory, name)
                if name.endswith(".py") and name != "project_rules.py":
                    try:
                        with open(path, encoding="utf-8") as handle:
                            text = handle.read()
                    except (OSError, ValueError):
                        text = "RequiredKey("  # unreadable, so its import reports UNLOADABLE
                    if DECLARATION.search(text):
                        found.append(path)
    return sorted(found)


def declarations(value, kinds):
    if isinstance(value, kinds):
        yield value
    elif isinstance(value, (tuple, list)):
        for entry in value:
            yield from declarations(entry, kinds)
    elif isinstance(value, dict):
        for entry in value.values():
            yield from declarations(entry, kinds)


def main(root):
    sys.path.insert(0, os.path.join(root, "gates", "scripts"))
    import project_rules
    kinds = (project_rules.RequiredKey, project_rules.OptionalKey)
    try:
        examples = example_values(root)
    except ValueError as error:
        print(error)
        return 1
    problems, checked = [], 0
    for index, path in enumerate(declaring_files(root)):
        relative = os.path.relpath(path, root)
        try:
            name = f"declaring_{index}"
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module  # as importlib's recipe registers a module it loads
            spec.loader.exec_module(module)
        except (Exception, SystemExit) as error:  # a module's own exit must not end this check
            problems.append(f"UNLOADABLE: {relative}: {error!r}")
            continue
        found = [declared for value in vars(module).values()
                 for declared in declarations(value, kinds)]
        if not found:
            problems.append(f"UNLOADABLE: {relative} holds no top-level declaration")
        for declared in found:
            checked += 1
            if declared.key not in examples:
                problems.append(f"UNDOCUMENTED: {relative}: {declared.key}")
                continue
            example = examples[declared.key]
            if not project_rules.is_unset(example):
                continue  # an illustration of a real value, which the key may well accept
            if (not project_rules.key_unset(declared, example)
                    and not project_rules.key_problems({declared.key: example}, [declared])):
                problems.append(f"ACCEPTS: {relative}: {declared.key} takes its placeholder "
                                f"{example!r} as a real setting")
    if not checked and not problems:
        problems.append("NOTHING DECLARED: no script under gates/ or skills/ declares a key")
    for problem in problems:
        print(problem)
    if not problems:
        print(f"ok: {checked} declared keys")
    return 1 if problems else 0


sys.exit(main(sys.argv[1]))
PY
