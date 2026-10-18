"""The project.json rules, the record-parsing rules, and the self-test helpers, the kit's
release, review, incident, maintenance, and retirement scripts share. Standard library only,
except fence_split, which loads the CommonMark parser vendored beside the README checker,
and YAML_VENDOR, the PyYAML the maintenance check loads.

Imported by skills/release/scripts/halt_watch.py,
skills/release-readiness/scripts/readiness_check.py, skills/ci-green/scripts/review_gate.py,
skills/incident-review/scripts/incident_check.py,
skills/maintenance-review/scripts/maintenance_check.py,
skills/retire-system/scripts/retire_check.py, gates/scripts/sarif_gate.py, and, for
the discipline rule alone, skills/write-tickets/scripts/lint_draft.py, so no two of
them can disagree on what an unset key, a placeholder, a discipline, a date, a printed
number, a branch slug, or a code fence is. Each importer's self-test covers the rules it
uses; this module has no entry point of its own.
"""
import ast
import datetime
import json
import math
import os
import re
import sys

GATES_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
# markdown-it-py, vendored beside the README checker so that skill can be copied alone; PyYAML,
# vendored here. Each loads only when a function needs it.
MARKDOWN_VENDOR = os.path.join(GATES_SCRIPTS, "..", "..", "skills", "readme-docs", "scripts",
                               "_vendor")
YAML_VENDOR = os.path.join(GATES_SCRIPTS, "_vendor")


def vendored(directory):
    """Put a vendor directory on the import path once, for the import that follows."""
    if directory not in sys.path:
        sys.path.insert(0, directory)

PLACEHOLDER = re.compile(r"^\s*<.*>\s*$")
# A value passed to a command as a bare argument: no option, path, or shell metacharacter.
BARE_FRAGMENT = r"[A-Za-z0-9_][A-Za-z0-9._-]*"
BARE_ARGUMENT = re.compile(rf"^{BARE_FRAGMENT}$")
REPO_PATH = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._/-]*$")
DISCIPLINES = ("security", "data-ml", "mobile", "embedded", "sre")
DECIMAL = r"-?\d+(?:\.\d+)?"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_unset(value):
    """Absent, blank, `none` in any case, or a README placeholder: a key nothing was
    configured for."""
    if value is None:
        return True
    if isinstance(value, str):
        return (not value.strip() or value.strip().lower() == "none"
                or PLACEHOLDER.match(value) is not None)
    return isinstance(value, list) and any(isinstance(entry, str) and PLACEHOLDER.match(entry)
                                           for entry in value)


def read_config(config_path):
    """project.json as a dict, or raise ValueError naming what is wrong."""
    try:
        with open(config_path, encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, ValueError) as error:
        raise ValueError(f"project.json unreadable: {error}")
    if not isinstance(config, dict):
        raise ValueError("project.json is not an object")
    return config


def named_disciplines(config):
    """The `disciplines` list, matched with case; absent is the README's default, []."""
    value = config.get("disciplines", [])
    if not (isinstance(value, list) and all(isinstance(name, str) for name in value)):
        raise ValueError("disciplines is not a list of names")
    unknown = [name for name in value if name not in DISCIPLINES]
    if unknown:
        raise ValueError(f"disciplines names {', '.join(map(repr, unknown))}, not one of "
                         + ", ".join(DISCIPLINES))
    return value


def check_repo_path(key, value):
    """A directory key written unquoted into commands: set, relative, inside the repository
    and outside .git, made only of characters no shell treats specially."""
    if (is_unset(value) or not isinstance(value, str) or not REPO_PATH.fullmatch(value)
            or os.path.isabs(value)
            or os.path.normpath(value).split(os.sep)[0] in ("..", ".", ".git")):
        raise ValueError(f"{key} {value!r} is not a relative path inside the repository "
                         "outside .git, starting with a letter, digit, or '_', and made only "
                         "of letters, digits, '.', '_', '-', and '/'")


def parse_date(value):
    """A `YYYY-MM-DD` calendar date, nothing before or after it."""
    if not DATE.fullmatch(value):
        raise ValueError(f"{value!r} is not YYYY-MM-DD")
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{value!r} is not a calendar date")


def is_date(value):
    """Whether parse_date reads the value."""
    try:
        parse_date(value)
    except ValueError:
        return False
    return True


def fence_split(text):
    """([(line, fenced)], unclosed): fenced is true for every line of a fenced or indented
    code block, its marker lines included, exactly as a CommonMark renderer shows them as
    code; unclosed is true when a fence runs to the end of its container without closing.
    Line ends are normalized as markdown-it normalizes them. Read
    by the vendored markdown-it-py, never a hand-rolled fence rule, so no line the renderer
    shows as text can be taken for code."""
    vendored(MARKDOWN_VENDOR)
    from markdown_it import MarkdownIt
    # markdown-it reads a lone \r as a line end too, so line numbers match only once both
    # line-end forms are newlines.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    fenced, unclosed = [False] * len(lines), False
    # Parsed with a final newline, which a Jira description usually lacks, so the content
    # count below is the same whether the source ends in one or not.
    for token in MarkdownIt("commonmark").parse(text if text.endswith("\n") else text + "\n"):
        if token.type not in ("fence", "code_block") or not token.map:
            continue
        start, end = token.map
        for number in range(start, min(end, len(lines))):
            fenced[number] = True
        # A closed fence's map holds its opener, its content lines, and its closer; one that
        # ran to the end of its container has no closer line.
        if token.type == "fence" and token.content.count("\n") == end - start - 1:
            unclosed = True
    return list(zip(lines, fenced)), unclosed


def check_slug(kind, value):
    """A name written into a branch and a path: lowercase kebab-case, nothing else."""
    if not SLUG.fullmatch(value):
        raise ValueError(f"{kind} {value!r} is not lowercase letters and digits joined by '-'")
    return value


def single_number(output, key):
    """The number a configured command printed: exactly one non-blank line, one decimal."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) != 1 or not re.fullmatch(DECIMAL, lines[0]):
        raise ValueError(f"{key} did not print exactly one decimal number")
    return lines[0]


def positive_int(key, value):
    """A count such as a number of days: a JSON integer above zero, never a bool or a string."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{key} {value!r} is not a whole number above zero")
    return value


def json_number(key, value):
    """A JSON number, finite, never a bool, which JSON-reading Python would take for one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{key} {value!r} is not a finite JSON number")
    return value


def check_command(key, value):
    """A configured command: a string, as the skills run it in a subshell."""
    if not isinstance(value, str):
        raise ValueError(f"{key} is not a command")
    return value


def imports_of(tree):
    """Top-level module names an AST imports absolutely. check_readme.py keeps its own copy
    and of foreign_code (its grammar_and_imports), so readme-docs still works copied without
    the rest of the kit; a fix to either lands in both."""
    names = {alias.name.split(".")[0] for node in ast.walk(tree)
             if isinstance(node, ast.Import) for alias in node.names}
    names |= {node.module.split(".")[0] for node in ast.walk(tree)
              if isinstance(node, ast.ImportFrom) and node.module and not node.level}
    return names


def foreign_code(sources, allowed):
    """(syntax errors, foreign imports) over the source files: a file that does not parse
    with the Python 3.8 grammar, and each module imported that is neither the standard
    library nor in allowed. Foreign imports are None before Python 3.10, which is the first
    to list the standard library."""
    syntax_errors, imported = [], set()
    for source in sources:
        with open(source, encoding="utf-8") as handle:
            text = handle.read()
        try:
            tree = ast.parse(text, feature_version=(3, 8))
        except SyntaxError as error:
            syntax_errors.append(f"{os.path.basename(source)}: {error}")
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue  # this interpreter cannot read it either, so it yields no imports
        imported |= imports_of(tree)
    stdlib = getattr(sys, "stdlib_module_names", None)
    return syntax_errors, (None if stdlib is None else sorted(imported - stdlib - set(allowed)))


def report(kind, name, got, expected):
    """One self-test line; 1 on a mismatch, so callers can sum failures."""
    if got == expected:
        print(f"ok   {kind}: {name}")
        return 0
    print(f"FAIL {kind}: {name} — expected {expected!r}, got {got!r}")
    return 1


def result_of(function, *arguments):
    """The function's result, or "ValueError" when it raises one."""
    try:
        return function(*arguments)
    except ValueError:
        return "ValueError"


def error_of(function, *arguments):
    """"ok" when the function returns, or "ValueError" when it raises one."""
    try:
        function(*arguments)
    except ValueError:
        return "ValueError"
    return "ok"
