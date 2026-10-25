"""The project.json rules, the record-parsing rules, the check-script entry point, and the
self-test helpers, the kit's release, review, incident, maintenance, retirement, and design
scripts share. Standard library only, except fence_split and markdown_tokens, which load the
CommonMark parser vendored beside the README checker, and YAML_VENDOR, the PyYAML the
maintenance check and scripts/ci/actions-pinned.sh load.

Imported by skills/release/scripts/halt_watch.py,
skills/release-readiness/scripts/readiness_check.py, skills/ci-green/scripts/review_gate.py,
skills/incident-review/scripts/incident_check.py,
skills/maintenance-review/scripts/maintenance_check.py,
skills/retire-system/scripts/retire_check.py,
skills/design-feature/scripts/design_check.py, gates/scripts/sarif_gate.py,
gates/scripts/adr_numbers.py, and, for the discipline, tracked-file and self-test git rules,
skills/write-tickets/scripts/lint_draft.py, and, for the YAML vendor alone,
scripts/ci/actions-pinned.sh, and, for the Markdown table, register and tracked-file rules,
scripts/ci/rule-book-map.sh, and, for the key registry, scripts/ci/config-examples.sh,
so no two of them can disagree on what an unset key, a placeholder, a discipline, a date, a
printed number, a branch slug, a code fence, a Markdown field's value, a Markdown table, a
register header, a complete exceptions-register row, a tracked path, or a git call and its
failure is, and so no self-test's scratch repository inherits the caller's git. Each
importer's self-test covers the rules it uses; this module has no entry point of its own.
"""
import ast
import contextlib
import datetime
import json
import math
import os
import re
import subprocess
import sys
import typing
from unittest import mock

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
    """Absent, blank, `none` in any case, or a `<placeholder>`: a key nothing was
    configured for."""
    if value is None:
        return True
    if isinstance(value, str):
        return (not value.strip() or value.strip().lower() == "none"
                or PLACEHOLDER.match(value) is not None)
    return isinstance(value, list) and any(isinstance(entry, str) and PLACEHOLDER.match(entry)
                                           for entry in value)


class RequiredKey(typing.NamedTuple):
    """A project.json key a check cannot run without, by its path in PROJECT_KEYS, such as
    `roles.service_owner`. Its shape is the registry's alone, as cfgv's Required names a key
    whose check the schema holds; needed_by names who needs it, for the message when unset."""
    key: str
    needed_by: typing.Optional[str] = None


class OptionalKey(typing.NamedTuple):
    """A project.json key that takes default when unset, named as RequiredKey is."""
    key: str
    default: typing.Any


def key_value(config, path):
    """The value at a dotted path, None where any part is absent; ValueError where a parent
    is set but not an object."""
    value, walked = config, []
    for part in path.split("."):
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError(f"{'.'.join(walked)} is not an object")
        value = value.get(part)
        walked.append(part)
    return value


def key_unset(shape, value):
    """Whether the value leaves a key of that shape unset: is_unset's scalar, or, for a
    template list, a list made wholly of placeholder entries, as the reference writes it."""
    if isinstance(value, list):
        return shape.template_list and bool(value) and all(
            isinstance(entry, str) and PLACEHOLDER.match(entry) for entry in value)
    return is_unset(value)


def check_value(path, shape, value):
    """Raise ValueError when a set value is not in the key's shape: a template list keeping
    a placeholder entry beside a real one, or a value its check rejects."""
    if shape.template_list and is_unset(value) and isinstance(value, list):
        raise ValueError(f"{path} still holds a placeholder entry")
    shape.check(value)


def key_problems(config, keys, registry=None):
    """The message of every problem with the declared keys in config, in order: a required key
    unset, or a set key not in its registered shape. registry defaults to PROJECT_KEYS; a path
    not in it raises KeyError."""
    registry = PROJECT_KEYS if registry is None else registry
    def judge(declared):
        if (not isinstance(getattr(declared, "needed_by", None), (str, type(None)))
                or callable(getattr(declared, "default", None))):
            raise TypeError(f"{declared.key} is declared with a check; a shape belongs in "
                            "PROJECT_KEYS")
        shape = registry[declared.key]
        value = key_value(config, declared.key)
        if not key_unset(shape, value):
            check_value(declared.key, shape, value)
        elif isinstance(declared, RequiredKey):
            needs = f", and {declared.needed_by} needs it" if declared.needed_by else ""
            raise ValueError(f"{declared.key} is absent, none, blank, or a placeholder{needs}")
    return collected_errors(lambda declared=declared: judge(declared) for declared in keys)


def read_keys(config, keys, registry=None):
    """{path: value} for the declared keys, an unset optional one at its default; raise naming
    every problem key_problems finds."""
    registry = PROJECT_KEYS if registry is None else registry
    problems = key_problems(config, keys, registry)
    if problems:
        raise ValueError("; ".join(problems))
    values = {}
    for declared in keys:
        value = key_value(config, declared.key)
        values[declared.key] = (declared.default if key_unset(registry[declared.key], value)
                                else value)
    return values


# Inline emphasis and code-span markers, which change how a Markdown value renders, not what
# it says: a snake_case underscore is not one, being inside a word. CommonMark's backslash
# escape of ASCII punctuation renders as the punctuation alone.
INLINE_MARKUP = re.compile(r"`|\*|~~|(?<!\w)_|_(?!\w)")
BACKSLASH_ESCAPE = re.compile(r"\\([!-/:-@\[-`{-~])")


def markdown_value(text):
    """A Markdown field's value as its reader sees it, without inline emphasis, code-span
    markers, or backslash escapes, so `none`, **<flag>** or \\<flag\\> is judged as what it shows."""
    return INLINE_MARKUP.sub("", BACKSLASH_ESCAPE.sub(r"\1", text)).strip()


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
    """The `disciplines` list, matched with case; absent is the documented default, []."""
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


def isolated_git_environment(**overrides):
    """The caller's environment for a self-test's scratch repository: no inherited GIT_DIR,
    GIT_INDEX_FILE or GIT_CONFIG_PARAMETERS to aim it at another repository or
    configuration, no user or system config, a fixed identity, then overrides."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_AUTHOR_NAME="t",
                       GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    environment.update(overrides)
    return environment


@contextlib.contextmanager
def process_state(environment, directory=None):
    """Run the block with os.environ replaced by environment and, given a directory, from
    it, for code under test that calls git with the caller's environment; both are put back
    however the block ends."""
    here = os.getcwd()
    with mock.patch.dict(os.environ, environment, clear=True):
        try:
            if directory is not None:
                os.chdir(directory)
            yield
        finally:
            os.chdir(here)


# git's global options whose value may follow as a separate word.
GIT_VALUE_OPTIONS = ("-c", "-C", "--git-dir", "--work-tree", "--namespace", "--config-env",
                     "--attr-source")


def git_subcommand(arguments):
    """The subcommand in a git argument list: the first word that is neither an option nor
    the separate value of one; None when there is none."""
    words = iter(arguments)
    for word in words:
        if word in GIT_VALUE_OPTIONS:
            next(words, None)
        elif not word.startswith("-"):
            return word
    return None


def run_git(root, *arguments, environment=None, text=True):
    """git's stdout, run in root, as text or with text False as bytes, or ValueError naming
    the subcommand that failed and git's last line of stderr; environment None is the
    caller's."""
    command = " ".join(filter(None, ("git", git_subcommand(arguments))))
    try:
        completed = subprocess.run(["git", *arguments], cwd=root, capture_output=True,
                                   check=False, env=environment)
    except OSError as error:
        raise ValueError(f"{command} failed: {error.strerror}")
    if completed.returncode != 0:
        message = os.fsdecode(completed.stderr).strip().splitlines()
        raise ValueError(f"{command} failed: "
                         f"{message[-1] if message else completed.returncode}")
    return completed.stdout.decode("utf8", "surrogateescape") if text else completed.stdout


def tracked_files(root):
    """Every path git tracks under root, as `git ls-files` writes it. A repo path matched
    against this exactly, not tested on disk, is absent when untracked, cased wrongly on a
    case-insensitive disk, or climbing out of the repo, as it is in a fresh checkout. A file
    inside a submodule is not listed; the submodule's own path is. Raises ValueError where
    git cannot list root."""
    try:
        listing = run_git(None, "-C", root, "ls-files", "-z", text=False)
    except ValueError as error:
        raise ValueError(f"cannot list the tracked files under {root}: {error}")
    return {os.fsdecode(name) for name in listing.split(b"\0") if name}


def tracked_path_matcher(root):
    """A test of whether git tracks a cited path under root, as a file or as a directory
    holding one, its trailing slashes ignored: the one rule every reader of a repo path
    applies. Raises ValueError where git cannot list root."""
    paths = tracked_files(root)
    for path in list(paths):
        parent = os.path.dirname(path)
        while parent:
            paths.add(parent)
            parent = os.path.dirname(parent)
    return lambda cited: cited.rstrip("/") in paths


# The exceptions register's columns, in order, as gates/exceptions.md's Format defines them.
REGISTER_COLUMNS = ("Rule", "Reason", "Risk", "Expiry", "Remediation")


def is_register_header(cells):
    """Whether a table's header opens with the register's columns; a register may add
    columns after them."""
    return tuple(cells[:len(REGISTER_COLUMNS)]) == REGISTER_COLUMNS


def complete_register_row(row):
    """Whether a register body row, its cells in REGISTER_COLUMNS order, records an
    exception at all: every cell filled, none a separator, and Expiry a date. Whether it has
    expired is the caller's question; a row missing its reason, risk, or remediation records
    none, since nothing says why the waiver holds or how it ends."""
    return (len(row) >= len(REGISTER_COLUMNS)
            and all(row[n] and not re.fullmatch(r":?-+:?", row[n])
                    for n in range(len(REGISTER_COLUMNS)))
            and is_date(row[REGISTER_COLUMNS.index("Expiry")]))


def is_date(value):
    """Whether parse_date reads the value."""
    try:
        parse_date(value)
    except ValueError:
        return False
    return True


def words(text):
    """The text with each run of whitespace read as one space."""
    return " ".join(text.split())


def markdown_tokens(text):
    """The document as the vendored CommonMark parser reads it, GFM tables on."""
    vendored(MARKDOWN_VENDOR)
    from markdown_it import MarkdownIt
    return MarkdownIt("commonmark").enable("table").parse(text)


def markdown_tables(tokens, section=None):
    """Each table as (header cells, body rows of cells). A header cell reads each run of
    whitespace as one space, as a renderer shows it; a body cell is its stripped source text,
    an escaped pipe unescaped, so a value is read exactly. A body row is padded or cut to the
    header's width, as GFM renders it. With section, only the tables under the heading of that
    text, up to the next heading at its level or above. A pipe line in a fence or prose is
    not a table, and an escaped pipe does not split a cell, as a renderer shows them."""
    found, level, in_section, cells = [], None, section is None, None
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and section is not None:
            if tokens[index + 1].content.strip() == section:
                level, in_section = token.tag, True
            elif level is not None and token.tag <= level:
                in_section = False
        elif not in_section:
            continue
        elif token.type == "table_open":
            found.append(([], []))
        elif token.type == "tr_open":
            cells = []
        elif token.type == "tr_close":
            header, rows = found[-1]
            if header:
                rows.append(cells)
            else:
                header.extend(cells)
        elif token.type == "inline" and tokens[index - 1].type == "th_open":
            cells.append(words(token.content))
        elif token.type == "inline" and tokens[index - 1].type == "td_open":
            cells.append(token.content.strip())
    return found


def fence_split(text):
    """([(line, fenced)], unclosed): fenced is true for every line of a fenced or indented
    code block, its marker lines included, exactly as a CommonMark renderer shows them as
    code; unclosed is true when a fence runs to the end of its container without closing.
    Line ends are normalized as markdown-it normalizes them. Read
    by the vendored markdown-it-py, never a hand-rolled fence rule, so no line the renderer
    shows as text can be taken for code."""
    # markdown-it reads a lone \r as a line end too, so line numbers match only once both
    # line-end forms are newlines.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    fenced, unclosed = [False] * len(lines), False
    # Parsed with a final newline, which a Jira description usually lacks, so the content
    # count below is the same whether the source ends in one or not.
    for token in markdown_tokens(text if text.endswith("\n") else text + "\n"):
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


DOTTED = r"\d+(?:\.\d+)*"
DEVICE = re.compile(rf"^({BARE_FRAGMENT}) ({DOTTED})$")
THRESHOLD = re.compile(rf"^({BARE_FRAGMENT}) ({DECIMAL})$")


def check_string_list(value, entry_fits, message):
    """Raise ValueError(message) unless value is a non-empty list of strings entry_fits
    accepts."""
    if not (isinstance(value, list) and value
            and all(isinstance(entry, str) and entry_fits(entry) for entry in value)):
        raise ValueError(message)


def device_entries(value):
    """device_matrix's `<os> <version>` entries as (os, version) pairs."""
    check_string_list(value, DEVICE.fullmatch, "device_matrix is not a non-empty list of "
                      "`<os> <version>` entries, the version dotted digits")
    return [DEVICE.fullmatch(entry).groups() for entry in value]


def threshold_entries(value):
    """model_eval_thresholds as given, once each entry is a `<metric> <minimum>` pair and no
    metric repeats, case aside."""
    check_string_list(value, THRESHOLD.fullmatch, "model_eval_thresholds is not a non-empty "
                      "list of `<metric> <minimum>` pairs, the minimum a decimal number")
    metrics = [THRESHOLD.fullmatch(entry).group(1).lower() for entry in value]
    if len(set(metrics)) != len(metrics):
        raise ValueError("model_eval_thresholds names a metric twice")
    return value


def glob_list(value):
    """security_sensitive_paths' globs, each one CODEOWNERS supports."""
    if not isinstance(value, str):
        raise ValueError("security_sensitive_paths is not a space-separated list of globs")
    unsupported = [pattern for pattern in value.split()
                   if pattern.startswith("!") or re.search(r"[\[\]\\]", pattern)]
    if unsupported:
        raise ValueError(f"security_sensitive_paths holds {', '.join(unsupported)}: CODEOWNERS "
                         "supports no `!` negation, `[ ]` ranges, or `\\` escapes")
    return value.split()


def check_min_version(value):
    """Raise ValueError unless min_supported_app_version is dotted digits."""
    if not (isinstance(value, str) and re.fullmatch(DOTTED, value)):
        raise ValueError("min_supported_app_version is not dotted digits")


def check_on_call(value):
    """Raise ValueError unless on_call is a non-empty list of one-word handles."""
    check_string_list(value, lambda person: person.split() == [person],
                      "on_call is not a non-empty list of handles, one word each")


def check_target(key, value):
    """Raise ValueError unless the key's value is a JSON number from 0 to 100."""
    json_number(key, value)
    if not 0 <= value <= 100:
        raise ValueError(f"{key} {value!r} is not a number from 0 to 100")


def check_halt_criteria(value):
    """Raise ValueError unless halt_criteria is a non-empty list of commands, none blank or a
    `<placeholder>`, as gates/release.md defines it."""
    check_string_list(value, lambda command: bool(command.strip()),
                      "halt_criteria is not a non-empty list of commands")
    if any(PLACEHOLDER.match(command) for command in value):
        raise ValueError("halt_criteria holds a <placeholder>, not a command")


def check_rollout_stages(value):
    """Exactly `none`, or the production stages in order, as gates/release.md defines them."""
    if value == "none":
        return
    check_string_list(value, lambda name: True,
                      "rollout_stages is neither none nor a non-empty list of names")
    for name in value:
        if not BARE_ARGUMENT.fullmatch(name) or name.lower() == "staging":
            raise ValueError(f"rollout_stages entry {name!r} is blank, staging, starts with "
                             "'-' or '.', or is not made only of letters, digits, '.', '_', "
                             "and '-'")
    if len(set(value)) != len(value):
        raise ValueError("rollout_stages repeats a stage")


def check_service_owner(value):
    """Raise ValueError unless roles.service_owner is a name."""
    if not isinstance(value, str):
        raise ValueError("roles.service_owner is not a name")


class KeyShape(typing.NamedTuple):
    """A project.json key's one shape: check(value) raises ValueError on a value not in it.
    With template_list, a list made wholly of placeholder entries, as
    reference/project-json.md's example writes the key, reads as unset."""
    check: typing.Callable
    template_list: bool = False


def keyed(check, *keys):
    """{key: KeyShape} for keys sharing a check that takes the key, then the value."""
    return {key: KeyShape(lambda value, key=key: check(key, value)) for key in keys}


# Every project.json key a kit script checks, by dotted path, so no two readers can hold
# different shapes for one key, as pre-commit declares a hook key once and derives each
# context's required-ness from it; disciplines, a fixed vocabulary, is named_disciplines'.
# Readers go through read_keys, except where a gate reads a key more strictly than its unset
# rule, as gates/release.md does halt_watch's, or where the value arrives as an argument;
# those call the shape's check directly. scripts/ci/config-examples.sh checks each against
# reference/project-json.md's example.
PROJECT_KEYS = {
    **keyed(check_repo_path, "design_dir", "adr_dir", "retirements_dir", "runbooks_dir",
            "alert_rules_dir", "release_dir", "incident_reviews_dir"),
    **keyed(check_command, "dependency_outdated_command", "alert_routes_command",
            "data_quality_command", "model_eval_command", "device_test_command",
            "hil_test_command", "api_compat_command", "error_budget_command",
            "drift_check_command"),
    **keyed(positive_int, "iteration_days", "patch_sla_days", "monitoring_window_minutes"),
    "halt_criteria": KeyShape(check_halt_criteria),
    "rollout_stages": KeyShape(check_rollout_stages),
    **keyed(json_number, "drift_threshold"),
    **keyed(check_target, "debt_share_target"),
    "on_call": KeyShape(check_on_call, template_list=True),
    "roles.service_owner": KeyShape(check_service_owner),
    "device_matrix": KeyShape(device_entries, template_list=True),
    "model_eval_thresholds": KeyShape(threshold_entries, template_list=True),
    "security_sensitive_paths": KeyShape(glob_list),
    "min_supported_app_version": KeyShape(check_min_version),
}


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


def result_of(function, *arguments, error=ValueError):
    """The function's result, or the error's name when it raises that error."""
    try:
        return function(*arguments)
    except error:
        return error.__name__


def run_check(parser, checks, command):
    """A check script's entry point: print the named check's result and exit 0, print
    `INVALID: <what>` to stderr and exit 1 when it raises ValueError, or print usage and exit
    2 when no check has that name."""
    if command not in checks:
        parser.print_usage(sys.stderr)
        return 2
    try:
        print(checks[command]())
    except ValueError as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1
    return 0


def cli_case(script, name, arguments, expected_output, expected_exit, **options):
    """One self-test line for a check script run as a subprocess: its stderr when the output
    expected is an `INVALID` line, else its stdout, read to the expected output's length and
    paired with the exit status. options pass to subprocess.run, such as input or cwd."""
    run = subprocess.run([sys.executable, script, *arguments], capture_output=True, text=True,
                         check=False, **options)
    stream = run.stderr if expected_output.startswith("INVALID") else run.stdout
    return report("cli", name, (stream.strip()[:len(expected_output)], run.returncode),
                  (expected_output, expected_exit))


def result_or_message(call):
    """The call's result, or the message of the ValueError it raises."""
    try:
        return call()
    except ValueError as error:
        return str(error)


def error_message(call):
    """The ValueError message the call raises, or None when it returns."""
    try:
        call()
    except ValueError as error:
        return str(error)
    return None


def collected_errors(calls):
    """The ValueError message of each call that raises one, in order, so a check can name
    every problem in one run rather than the first."""
    return [message for message in map(error_message, calls) if message is not None]


def error_of(function, *arguments):
    """"ok" when the function returns, or "ValueError" when it raises one."""
    try:
        function(*arguments)
    except ValueError:
        return "ValueError"
    return "ok"
