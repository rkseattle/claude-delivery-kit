#!/usr/bin/env bash
# No project.json key in project_rules.PROJECT_KEYS, the registry of every key a kit script
# checks, accepts the placeholder reference/project-json.md writes for it as a real
# setting: each such example reads as unset or is rejected by the key's registered shape, so
# a template copied unedited never configures anything. A registered key the example blocks
# never show, at its dotted path such as roles.service_owner, fails too. A root with no
# registry, a reference with no example block, or an empty registry fails rather than
# reading as clean. So does a RequiredKey or OptionalKey a kit script declares at its top
# level, by a literal path as its first argument or its key=, called bare or as an attribute
# such as project_rules.RequiredKey, that the registry does not hold, found by parsing the kit's
# Python under gates/ and skills/ without importing it; a declaration inside a function, such
# as a self-test fixture or one built from a variable, is left to that script's self-test.
#
# Only an example that is wholly a placeholder, or a list holding one, is judged: any other
# illustrates a real value, which the key may well accept, and a placeholder embedded in a
# longer string, such as a path, is not read as one.
# Usage: config-examples.sh [repo-root]
set -euo pipefail
root="$(cd "${1:-.}" && pwd)"
python3 - "$root" <<'PY'
import ast
import json
import os
import sys

sys.dont_write_bytecode = True


def example_values(root, project_rules):
    """The keys the reference's example blocks show, merged; raise ValueError when there is
    none to read. A block is a fenced code block whose info string's first word is json, in
    either fence character, read by the vendored CommonMark parser as a renderer shows it."""
    path = os.path.join(root, "reference", "project-json.md")
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        blocks = [project_rules.json_text(token.content, "a json block")
                  for token in project_rules.markdown_tokens(text)
                  if token.type == "fence" and token.info.split()[:1] == ["json"]]
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
    return values


def shown(examples, path):
    """Whether the examples hold every part of the dotted path."""
    value = examples
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return True


def top_level_paths(tree):
    """Each literal path a RequiredKey or OptionalKey call names outside every function."""
    pending = list(ast.iter_child_nodes(tree))
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        called = getattr(node, "func", None)
        name = getattr(called, "id", None) or getattr(called, "attr", None)
        if isinstance(node, ast.Call) and name in ("RequiredKey", "OptionalKey"):
            keys = node.args[:1] + [word.value for word in node.keywords if word.arg == "key"]
            yield from (key.value for key in keys
                        if isinstance(key, ast.Constant) and isinstance(key.value, str))
        pending.extend(ast.iter_child_nodes(node))


def unregistered(root, registry):
    """A problem line for each top-level declaration of a path the registry lacks, and for
    each kit script that cannot be read or parsed."""
    problems = []
    for top in ("gates", "skills"):
        for directory, subdirectories, files in os.walk(os.path.join(root, top)):
            subdirectories[:] = sorted(d for d in subdirectories
                                       if d not in ("_vendor", "__pycache__"))
            for name in sorted(files):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(directory, name)
                relative = os.path.relpath(path, root)
                try:
                    with open(path, encoding="utf-8") as handle:
                        tree = ast.parse(handle.read())
                except (OSError, ValueError, SyntaxError) as error:
                    problems.append(f"UNREADABLE: {relative}: {error}")
                    continue
                problems.extend(f"UNREGISTERED: {relative}: {key}"
                                for key in top_level_paths(tree) if key not in registry)
    return problems


def main(root):
    rules = os.path.join(root, "gates", "scripts", "project_rules.py")
    if not os.path.isfile(rules):
        print(f"NO SCHEMA: {rules} is missing")
        return 1
    sys.path.insert(0, os.path.dirname(rules))
    import project_rules
    try:
        examples = example_values(root, project_rules)
    except ValueError as error:
        print(error)
        return 1
    problems = unregistered(root, project_rules.PROJECT_KEYS)
    for path, shape in project_rules.PROJECT_KEYS.items():
        if not shown(examples, path):
            problems.append(f"UNDOCUMENTED: {path}")
            continue
        example = project_rules.key_value(examples, path)
        if not (project_rules.is_unset(example) or project_rules.holds_placeholder(example)):
            continue  # an illustration of a real value, which the key may well accept
        if (not project_rules.key_unset(shape, example) and project_rules.error_message(
                lambda: project_rules.check_value(path, shape, example)) is None):
            problems.append(f"ACCEPTS: {path} takes its placeholder {example!r} as a real "
                            "setting")
    if not project_rules.PROJECT_KEYS:
        problems.append("NOTHING DECLARED: project_rules.PROJECT_KEYS is empty")
    for problem in problems:
        print(problem)
    if not problems:
        print(f"ok: {len(project_rules.PROJECT_KEYS)} registered keys")
    return 1 if problems else 0


sys.exit(main(sys.argv[1]))
PY
