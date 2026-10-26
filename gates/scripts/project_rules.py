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
scripts/ci/rule-book-map.sh, and, for the key registry, scripts/ci/config-examples.sh, and
run by skills/plan-project/SKILL.md for its slug, skills/write-tickets/SKILL.md for its
draft's, a design path, and the design's Epic key, skills/plan-work/SKILL.md for a design
path and its ADR paths, skills/implement-phases/SKILL.md for its branch,
skills/ci-green/SKILL.md for its PR number, skills/design-feature/SKILL.md for its Epic key,
and skills/release-readiness/SKILL.md for the keys a release covers,
so no two of them can disagree on a key's shape, what an unset key, a placeholder, a
discipline, a date, a printed number, a branch slug, a code fence, a Markdown field's value,
a Markdown table, a register header, a complete exceptions-register row, a tracked path, a
self-test's scratch file, or a git call and its failure is, and so no self-test's scratch
repository inherits the caller's git. Each importer's self-test covers the rules it uses.

    project_rules.py pr-number          the pull request number on standard input, as digits;
                                   INVALID for anything else
    project_rules.py slug [--title TITLE]
                                   the title, or standard input, as a slug, per slug_of,
                                   fitted to a bare branch name's lock file; INVALID when no
                                   letter or digit is left; for a skill with no script of
                                   its own, or whose script derives no slug, when the slug
                                   takes no prefix
    project_rules.py ticket-key [--prefix KEY]
                                   the Jira key on standard input, when it is one and under
                                   --prefix; INVALID otherwise
    project_rules.py ticket-keys --prefix KEY
                                   every distinct key under KEY that standard input names
    project_rules.py draft-slug     the request on standard input as write-tickets' draft
                                   slug, fitted to DRAFT_SLUG_MAX
    project_rules.py ticket-branch [--prefix KEY]
                                   `<KEY>-<slug>` from standard input's ticket key line and
                                   the words after it, the whole fitted to a branch's lock
                                   file; INVALID for a malformed key, or one outside --prefix
    project_rules.py design-path --dir DIR [--key KEY]
                                   the design or ADR path on standard input, when it is
                                   one repository path `DIR/<slug>.md` with no empty, `.`,
                                   or `..` component; INVALID otherwise, naming KEY,
                                   design_dir by default, for a bad DIR
    project_rules.py --self-test   runs the key registry's own cases and those of JIRA_KEY,
                                   slug_of, pr_number, ticket_branch, text_input, run_check,
                                   collected_errors, cli_case, write_scratch, and each
                                   subcommand; exit 0 only if each one matches

"""
import argparse
import ast
import contextlib
import datetime
import io
import itertools
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import typing
import unicodedata
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
    """Absent, blank, `none` in any case, or a `<placeholder>`: a scalar nothing was
    configured for. A list is never unset here; key_unset judges a key's list by its shape."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or value.strip().lower() == "none" or is_placeholder(value)
    return False


def is_placeholder(value):
    """Whether the value is text that is wholly a `<placeholder>`."""
    return isinstance(value, str) and PLACEHOLDER.match(value) is not None


def holds_placeholder(value):
    """Whether the value is a list with a `<placeholder>` entry."""
    return isinstance(value, list) and any(map(is_placeholder, value))


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
    """Whether the value leaves a key of that shape unset, the one rule every reader applies:
    is_unset's scalar, or, for a template list, a list made wholly of placeholder entries, as
    the reference writes it."""
    if isinstance(value, list):
        return shape.template_list and bool(value) and all(map(is_placeholder, value))
    return is_unset(value)


def check_value(path, shape, value):
    """Raise ValueError when a set value is not in the key's shape: a template list keeping
    a placeholder entry beside a real one, or a value its check rejects."""
    if shape.template_list and holds_placeholder(value):
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
    unset = unset_keys(config, keys, registry)
    return {declared.key: declared.default if declared.key in unset
            else key_value(config, declared.key) for declared in keys}


def unset_keys(config, keys, registry=None):
    """The paths of the declared keys config leaves unset, by key_unset."""
    registry = PROJECT_KEYS if registry is None else registry
    return {declared.key for declared in keys
            if key_unset(registry[declared.key], key_value(config, declared.key))}


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
    and outside any .git, made only of characters no shell treats specially. As git's
    verify_path does, it rejects an empty, `.`, or `..` component, trailing slashes aside, and
    a .git component anywhere in the path, case-insensitively and with trailing dots dropped,
    since a case-insensitive disk reads .GIT as .git, Windows reads .git. as .git, and git
    tracks nothing under one."""
    parts = value.rstrip("/").split("/") if isinstance(value, str) else []
    if (is_unset(value) or not isinstance(value, str) or not REPO_PATH.fullmatch(value)
            or os.path.isabs(value) or any(part in ("", ".", "..") for part in parts)
            or any(part.rstrip(".").casefold() == ".git" for part in parts)):
        raise ValueError(f"{key} {value!r} is not a relative path inside the repository with no "
                         "empty, '.', or '..' component, no '.git' component in any case "
                         "with or without trailing dots, starting with a "
                         "letter, digit, or '_', and made only of letters, digits, '.', '_', "
                         "'-', and '/'")


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


def text_input(value):
    """value when given, else standard input less its trailing line endings: how a check
    script takes text a person or Jira wrote, from a file redirected to standard input per
    gates/project-config.md's Untrusted text, so it never passes through a shell argument."""
    if value is not None:
        return value
    if sys.stdin.isatty():
        raise ValueError("no value was given, and standard input is a terminal")
    return sys.stdin.read().rstrip("\r\n")


NO_LETTER = "title {!r} holds no letter or digit a slug can keep"
# 255 bytes is the longest file name macOS and Linux allow; a slug is ASCII, so one character
# is one byte. A branch's lock file, `<slug>.lock`, is the shortest affix any caller adds.
FILE_NAME_MAX = 255
BRANCH_SLUG_MAX = FILE_NAME_MAX - len(".lock")


PR_NUMBER = re.compile(r"#?([1-9][0-9]*)")
# A Jira project key is an uppercase letter and one or more uppercase letters, digits, or
# underscores, as Atlassian requires; an issue key is one, a hyphen, and the issue number.
JIRA_PROJECT_KEY = r"[A-Z][A-Z0-9_]+"
JIRA_KEY = JIRA_PROJECT_KEY + r"-[1-9][0-9]*"
TICKET_KEY = re.compile(JIRA_KEY)


# A Jira key is short in practice; this leaves the slug room for at least a few words.
TICKET_KEY_MAX = 64


def project_prefix(prefix):
    """prefix, when it is a Jira project key; ValueError otherwise."""
    if not re.fullmatch(JIRA_PROJECT_KEY, prefix):
        raise ValueError(f"--prefix {prefix!r} is not a Jira project key")
    return prefix


def ticket_key(text, prefix=None):
    """text, stripped, when the whole of it is one Jira key of at most TICKET_KEY_MAX
    characters, under prefix when given; ValueError otherwise."""
    key = text.strip()
    if not TICKET_KEY.fullmatch(key) or len(key) > TICKET_KEY_MAX:
        raise ValueError(f"{key!r} is not a Jira key")
    if prefix is not None and not key.startswith(f"{project_prefix(prefix)}-"):
        raise ValueError(f"{key!r} is not a {prefix} key")
    return key


def design_path(path, directory, key="design_dir"):
    """path, unchanged, when it is one repository path, as check_repo_path judges it, of the
    form `<directory>/<slug>.md`, SLUG's slug, as design-feature names its design docs and
    ADRs; directory, the value of key, is checked by check_repo_path as the key registry
    checks it. ValueError otherwise, naming key for a bad directory. A design or ADR path a
    request or a Jira field names reaches a command only as this prints it."""
    check_repo_path(key, directory)
    check_repo_path("path", path)
    *parents, name = path.split("/")
    if not name.endswith(".md") or not SLUG.fullmatch(name[:-len(".md")]):
        raise ValueError(f"path {path!r} does not end in a <slug>.md file name")
    if "/".join(parents) != directory.rstrip("/"):
        raise ValueError(f"path {path!r} is not directly under {key} {directory!r}")
    return path


def ticket_branch(text, prefix=None):
    """`<KEY>-<slug>` from a ticket key on the first line, checked by ticket_key, and a few
    words naming the change after it, the slug fitted so the branch's lock file,
    `<KEY>-<slug>.lock`, fits a file name. ValueError as ticket_key raises it, or for words
    with no letter or digit."""
    key_line, _, words = text.partition("\n")
    key = ticket_key(key_line, prefix)
    return f"{key}-{slug_of(words, BRANCH_SLUG_MAX - len(key) - 1)}"


def ticket_keys(text, prefix):
    """Every distinct key under prefix that text names, sorted: the tickets a range of commit
    subjects covers."""
    project_prefix(prefix)
    found = re.findall(r"(?<![A-Z0-9_])" + JIRA_KEY + r"(?![0-9])", text)
    return sorted({key for key in found if key.startswith(f"{prefix}-")})


# write-tickets' longest name from its draft slug is a ticket's readback copy,
# `<slug>.<KEY>.md`.
DRAFT_SLUG_MAX = FILE_NAME_MAX - len(".") - TICKET_KEY_MAX - len(".md")


def pr_number(value):
    """A pull request's number, a leading `#` allowed, as digits alone."""
    match = PR_NUMBER.fullmatch(value.strip())
    if not match:
        raise ValueError(f"{value!r} is not a pull request number")
    return match.group(1)


def slug_of(title, max_length=BRANCH_SLUG_MAX):
    """The title in lowercase kebab-case: NFKD-normalized, each character with no ASCII form
    dropped, lowercased, each run of characters other than a-z and 0-9 one hyphen, hyphens
    trimmed, then words dropped from the end until it fits max_length, a single word cut to
    it. ValueError when no letter or digit is left. A caller passes the file-name limit less
    the longest affix it writes the slug with."""
    folded = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    words = "".join(c if c.isalnum() else " " for c in folded.lower()).split()
    while len("-".join(words)) > max_length and len(words) > 1:
        words.pop()
    slug = "-".join(words)[:max_length]
    if not slug:
        raise ValueError(NO_LETTER.format(title))
    return check_slug("slug", slug)


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
    if holds_placeholder(value):
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


def tier_names(value):
    """The tiers verification_tiers names, lowercased: its prose split on `·`, commas,
    semicolons, `and` and `or`, each tier's parenthesized note dropped first, since a note may
    hold commas or parentheses of its own; ValueError when it is not text or names none."""
    if not isinstance(value, str):
        raise ValueError("verification_tiers is not text")
    plain = value
    while re.search(r"\([^()]*\)", plain):
        plain = re.sub(r"\([^()]*\)", "", plain)
    plain = plain.replace("`", "")
    tiers = {words(part).lower()
             for part in re.split(r"[·,;]|\b(?:and|or)\b", plain, flags=re.I)} - {""}
    if not tiers:
        raise ValueError("verification_tiers declares no tiers")
    return tiers


def keyed(check, *keys):
    """{key: KeyShape} for keys sharing a check that takes the key, then the value."""
    return {key: KeyShape(lambda value, key=key: check(key, value)) for key in keys}


# Every project.json key a kit script checks, by dotted path, so no two readers can hold
# different shapes for one key, as pre-commit declares a hook key once and derives each
# context's required-ness from it; disciplines, a fixed vocabulary, is named_disciplines', and
# reviewers, any comma-separated text, is review_gate.py's.
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
    "verification_tiers": KeyShape(tier_names),
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


SCRATCH_NUMBERS = itertools.count()  # write_scratch's unnamed files, one number per call


def write_scratch(directory, content, name=None):
    """A self-test's scratch file, written one way for every self-test: content as is when
    text (UTF-8) or bytes, and as JSON otherwise, such as a project.json or a SARIF report,
    to name, a path under directory whose folders are made as needed; returns the path.
    With no name, each call writes a file of its own, `scratch-<n>.json`."""
    path = os.path.join(directory, name or f"scratch-{next(SCRATCH_NUMBERS)}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(content, bytes):
        with open(path, "wb") as handle:
            handle.write(content)
    else:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content if isinstance(content, str) else json.dumps(content))
    return path


def result_of(function, *arguments, error=ValueError):
    """The function's result, or the error's name when it raises that error."""
    try:
        return function(*arguments)
    except error:
        return error.__name__


class Outcome(typing.NamedTuple):
    """A check's result when it is more than text to print and exit 0: the text for stdout,
    the exit status, and the lines for stderr, such as a row-by-row check's failures."""
    output: str
    status: int = 0
    errors: typing.Tuple[str, ...] = ()


def passed(check):
    """The check as one that prints `ok` when it returns: a check whose only result is that it
    raised nothing."""
    def checked():
        check()
        return "ok"
    return checked


def mismatch(check):
    """passed(check), its ValueError reported as `MISMATCH: <what>` and exit 1, for a check
    script whose documented failure prefix is MISMATCH rather than INVALID."""
    def compared():
        try:
            return passed(check)()
        except ValueError as error:
            return Outcome("", 1, (f"MISMATCH: {error}",))
    return compared


def run_check(parser, checks, command):
    """A check script's entry point: run the named check and print its result.

    - text: printed, nothing when empty, as a check finding no rows returns; exit 0
    - a list: printed one item per line; exit 0
    - an Outcome: its output printed, its errors to stderr; exit its status
    - a ValueError or OSError raised: `INVALID: <what>` to stderr; exit 1
    - no check of that name: usage to stderr; exit 2
    """
    if command not in checks:
        parser.print_usage(sys.stderr)
        return 2
    try:
        result = checks[command]()
    except (ValueError, OSError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1
    if isinstance(result, list):
        result = "\n".join(result)
    if isinstance(result, str):
        result = Outcome(result)
    if not isinstance(result, Outcome):
        raise TypeError(f"check {command!r} returned {type(result).__name__}, not text, a "
                        "list, or an Outcome")
    if result.output.rstrip("\n") != "":
        print(result.output.rstrip("\n"))
    for line in result.errors:
        print(line, file=sys.stderr)
    return result.status


def cli_case(script, name, arguments, expected_output, expected_exit, line=None,
             stderr_prefixes=("INVALID",), exact=False, **options):
    """One self-test line for a check script run as a subprocess: its stderr when the output
    expected starts with one of stderr_prefixes, else its stdout, stripped and cut to the line
    at index line when one is given, empty when there is no such line; compared whole when
    exact, else read to the expected output's length, so an empty one checks the exit status
    alone; paired with the exit status. options pass to subprocess.run, such as input or
    cwd."""
    run = subprocess.run([sys.executable, script, *arguments], capture_output=True, text=True,
                         check=False, **options)
    shown = (run.stderr if expected_output.startswith(stderr_prefixes) else run.stdout).strip()
    if line is not None:
        lines = shown.splitlines()
        shown = lines[line] if -len(lines) <= line < len(lines) else ""
    return report("cli", name, (shown if exact else shown[:len(expected_output)],
                                run.returncode), (expected_output, expected_exit))


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


def self_test():
    """The key registry's cases, over a fixture registry of two plain keys, a template list,
    and a key inside an object, and those of slug_of, JIRA_KEY, pr_number, ticket_branch,
    text_input, run_check, collected_errors, cli_case, write_scratch, and each subcommand; 1 if
    any fails. Every fixture is declared inside this function, so
    scripts/ci/config-examples.sh, which scans top-level declarations, skips them."""
    def text(key):
        def check(value):
            if not isinstance(value, str):
                raise ValueError(f"{key} is not text")
        return check

    def raise_empty():
        raise ValueError("")

    unset_k = "k is absent, none, blank, or a placeholder"
    read_keys_cases = [
        ("a required key unset is named", {}, [RequiredKey("k")], unset_k),
        ("a required key says who needs it", {"k": "none"}, [RequiredKey("k", needed_by="mobile")],
         unset_k + ", and mobile needs it"),
        ("an optional key unset takes its default", {"k": "<k>"}, [OptionalKey("k", 7)], {"k": 7}),
        ("a set key is checked", {"k": 5}, [OptionalKey("k", 7)], "k is not text"),
        ("a template list of placeholders reads as unset", {"t": ["<handle>", "<handle>"]},
         [OptionalKey("t", 7)], {"t": 7}),
        ("a template list keeping a placeholder beside a real entry is named",
         {"t": ["rob", "<handle>"]}, [OptionalKey("t", 7)], "t still holds a placeholder entry"),
        ("an empty template list is checked", {"t": []}, [OptionalKey("t", 7)], "t is not text"),
        ("any other list holding a placeholder is checked", {"k": ["<handle>"]},
         [OptionalKey("k", 7)], "k is not text"),
        ("every problem is named", {"j": 5}, [RequiredKey("k"), RequiredKey("j")],
         unset_k + "; j is not text"),
        ("a required template list reads as unset", {"t": ["<os> <version>"]}, [RequiredKey("t")],
         "t is absent, none, blank, or a placeholder"),
        ("a key inside an object is read by its path", {"roles": {"k": "rob"}},
         [OptionalKey("roles.k", None)], {"roles.k": "rob"}),
        ("a key under an absent object is unset", {}, [OptionalKey("roles.k", None)],
         {"roles.k": None}),
        ("a key under a null object is unset", {"roles": None}, [OptionalKey("roles.k", None)],
         {"roles.k": None}),
        ("a key under a non-object is named", {"roles": 5}, [OptionalKey("roles.k", None)],
         "roles is not an object"),
        ("a key under an empty list is named", {"roles": []}, [OptionalKey("roles.k", None)],
         "roles is not an object"),
        ("a deeper non-object parent is named by its path", {"a": {"b": 5}},
         [OptionalKey("a.b.c", None)], "a.b is not an object"),
        ("a template list mixing a placeholder and a non-text entry is checked",
         {"t": ["<handle>", 5]}, [OptionalKey("t", 7)], "t still holds a placeholder entry"),
    ]
    fixture_keys = {"k": KeyShape(text("k")), "j": KeyShape(text("j")),
                    "t": KeyShape(text("t"), template_list=True),
                    "roles.k": KeyShape(text("roles.k")), "a.b.c": KeyShape(text("a.b.c"))}
    failures = 0
    words_at_max = "-".join(["abcdefg"] * 31)  # 31 words of 7 letters and 30 hyphens: 247

    slug_cases = [
        ("a plain title", "Design and plan a feature", 247, "design-and-plan-a-feature"),
        ("punctuation runs are one hyphen", "Add a design-feature skill: writes, reviews!", 247,
         "add-a-design-feature-skill-writes-reviews"),
        ("ends are trimmed", "  --Cache eviction--  ", 247, "cache-eviction"),
        ("digits are kept, a dot separates", "OAuth 2.0 login", 247, "oauth-2-0-login"),
        ("accents fold to ASCII", "Café menü", 247, "cafe-menu"),
        ("a letter with no ASCII form is dropped", "Straße Søren Æther", 247, "strae-sren-ther"),
        ("underscores are separators", "rate_limit per_user", 247, "rate-limit-per-user"),
        ("backticks and slashes are separators", "Move `gates/scripts` out", 247,
         "move-gates-scripts-out"),
        ("words at the limit are kept", words_at_max.replace("-", " "), 247, words_at_max),
        ("one over the limit drops the last word", words_at_max.replace("-", " ") + "h", 247,
         "-".join(["abcdefg"] * 30)),
        ("one word at the limit is kept", "b" * 247, 247, "b" * 247),
        ("one word over the limit is cut", "a" * 248, 247, "a" * 247),
        ("a first word over the limit is cut, the rest dropped", "a" * 300 + " b", 247, "a" * 247),
        ("the default limit is a bare branch's", "c" * 300, None, "c" * 250),
        ("no ASCII letter or digit", "日本語", 247, NO_LETTER.format("日本語")),
        ("empty", "", 247, NO_LETTER.format("")),
        ("only punctuation", "-- ! --", 247, NO_LETTER.format("-- ! --")),
    ]
    for name, title, max_length, expected in slug_cases:
        arguments = (title,) if max_length is None else (title, max_length)
        failures += report("slug_of", name, result_or_message(lambda: slug_of(*arguments)),
                           expected)
    for name, config, keys, expected in read_keys_cases:
        failures += report("read_keys", name,
                           result_or_message(lambda: read_keys(config, keys, fixture_keys)),
                           expected)
    failures += report("is_placeholder", "padded text, not text, and text around one",
                       [is_placeholder(value) for value in ("  <x>  ", 5, None, "a <x>")],
                       [True, False, False, False])
    failures += report("read_keys", "a path not in the registry is a KeyError",
                       result_of(read_keys, {}, [OptionalKey("x", None)], fixture_keys,
                                 error=KeyError), "KeyError")
    failures += report("read_keys", "a check passed as needed_by or a default is a TypeError",
                       [result_of(read_keys, {}, [declared], fixture_keys, error=TypeError)
                        for declared in (RequiredKey("k", text("k")), OptionalKey("k", text("k")))],
                       ["TypeError"] * 2)
    failures += report("read_keys", "the registry defaults to PROJECT_KEYS",
                       result_or_message(lambda: read_keys({"design_dir": "/abs"},
                                                           [OptionalKey("design_dir", None)])),
                       error_message(lambda: check_repo_path("design_dir", "/abs")))
    for name, value, accepted in [("a trailing slash is kept", "docs/design/", True),
                                  ("an empty component", "docs//design", False),
                                  ("a '.' component", "docs/./design", False),
                                  ("a trailing '.' component", "docs/design/.", False),
                                  ("a '..' that stays inside", "docs/x/../design", False)]:
        failures += report("check_repo_path", name,
                           error_message(lambda value=value: check_repo_path("k", value)) is None,
                           accepted)
    printed, errors = io.StringIO(), io.StringIO()
    checks = {"empty": lambda: "", "rows": lambda: ["a", "b"], "invalid": raise_empty}
    with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(errors):
        exits = [run_check(argparse.ArgumentParser(prog="p"), checks, command)
                 for command in ("empty", "rows", "invalid", "missing")]
    outcomes = {"outcome": lambda: Outcome("row\n", 1, ("INVALID: one", "INVALID: two")),
                "same": mismatch(lambda: None), "differs": mismatch(lambda: int("x")),
                "unreadable": lambda: open(os.path.join(os.devnull, "x"))}
    outcome_out, outcome_err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(outcome_out), contextlib.redirect_stderr(outcome_err):
        outcome_exits = [run_check(None, outcomes, command) for command in outcomes]
    failures += report("run_check", "an Outcome, mismatch, and an OSError, by exit and stream",
                       (outcome_exits, outcome_out.getvalue(),
                        outcome_err.getvalue().splitlines()[:3],
                        (outcome_err.getvalue().splitlines() + [""] * 4)[3].startswith(
                            "INVALID: [Errno")),
                       ([1, 0, 1, 1], "row\nok\n",
                        ["INVALID: one", "INVALID: two",
                         "MISMATCH: invalid literal for int() with base 10: 'x'"], True))
    failures += report("run_check", "rows print, an empty result prints no blank line",
                       printed.getvalue(), "a\nb\n")
    failures += report("run_check", "exit 0 on a result, 1 on a ValueError, 2 on no such check",
                       exits, [0, 0, 1, 2])
    failures += report("run_check", "a ValueError prints INVALID and no check prints usage",
                       errors.getvalue().splitlines(), ["INVALID: ", "usage: p [-h]"])
    failures += report("run_check", "a check returning anything else is a TypeError",
                       result_of(run_check, None, {"none": lambda: None}, "none",
                                 error=TypeError), "TypeError")
    failures += report("collected_errors", "a ValueError with no message still counts",
                       collected_errors([raise_empty, lambda: None]), [""])
    with tempfile.TemporaryDirectory() as directory:
        written = [write_scratch(directory, {"k": "v"}, "repo/.claude/project.json"),
                   write_scratch(directory, "{ raw é }", "raw.json"),
                   write_scratch(directory, b"\xff", "raw.bin")]
        contents = []
        for path in written:
            with open(path, "rb") as handle:
                contents.append(handle.read())
        failures += report("write_scratch", "JSON serialized, text and bytes as is, folders made",
                           contents, [b'{"k": "v"}', "{ raw é }".encode("utf-8"), b"\xff"])
        script = write_scratch(directory, "import sys\nprint('a\\nb')\n"
                               "print('MISMATCH: x', file=sys.stderr)\nsys.exit(1)\n", "lines.py")
        silent = write_scratch(directory, "import sys\nprint('INVALID: y', file=sys.stderr)\n"
                               "sys.exit(1)\n", "silent.py")
        for case in [("the line at index -1, read from stdout", [], "b", 1, {"line": -1}),
                     ("a named prefix reads stderr", [], "MISMATCH: x", 1,
                      {"stderr_prefixes": ("INVALID", "MISMATCH")}),
                     ("exact compares the whole stream", [], "a\nb", 1, {"exact": True})]:
            failures += cli_case(script, *case[:4], **case[4])
        failures += cli_case(silent, "INVALID reads stderr by default", [], "INVALID: y", 1)
        failures += cli_case(silent, "an empty stream with a line index reads as empty", [], "",
                             1, line=0, exact=True)
        failures += cli_case(script, "a line index past the end reads as empty", [], "", 1,
                             line=5, exact=True)
        failures += cli_case(script, "a line index before the start reads as empty", [], "", 1,
                             line=-3, exact=True)
        failures += cli_case(script, "a prefix match passes longer output", [], "a", 1)
        failures += cli_case(script, "an empty expectation checks the exit alone", [], "", 1)
        with contextlib.redirect_stdout(io.StringIO()):
            beyond = cli_case(script, "beyond", [], "a", 1, exact=True)
        failures += report("cli_case", "exact fails on output beyond the expected", beyond, 1)
        unnamed = [write_scratch(directory, {"a": 1}), write_scratch(directory, {"a": 1})]
        failures += report("write_scratch", "each unnamed call writes a file of its own",
                           (unnamed[0] != unnamed[1], [read_config(path) for path in unnamed]),
                           (True, [{"a": 1}, {"a": 1}]))
    this = os.path.abspath(__file__)
    failures += cli_case(this, "slug prints the slug", ["slug", "--title", "My Project!"],
                         "my-project", 0, exact=True)
    failures += cli_case(this, "a slug of no letter is invalid", ["slug", "--title", "日本語"],
                         "INVALID: title ", 1)
    failures += cli_case(this, "slug reads the title from stdin", ["slug"], "rob-s-big-project",
                         0, input="Rob's (big project\n", exact=True)
    failures += cli_case(this, "--title wins over stdin", ["slug", "--title", "Given"], "given",
                         0, input="Piped\n")
    failures += cli_case(this, "pr-number prints the digits", ["pr-number"], "42", 0,
                         input="#42\n", exact=True)
    failures += cli_case(this, "a pr-number holding shell text is invalid", ["pr-number"],
                         "INVALID:", 1, input="42; touch x\n")
    for name, value, expected in [
            ("digits", "42", "42"), ("a leading #", "#42", "42"),
            ("surrounding whitespace", " 42 \n", "42"), ("zero", "0", "ValueError"),
            ("a leading zero", "042", "ValueError"), ("a bare #", "#", "ValueError"),
            ("empty", "", "ValueError"), ("a non-ASCII digit", "٤٢", "ValueError"),
            ("a URL", "https://github.com/o/r/pull/42", "ValueError"),
            ("a sign", "-42", "ValueError")]:
        failures += report("pr_number", name, result_of(pr_number, value), expected)
    for name, text, expected in [
            ("a key and words", "AB-12\nDesign feature skill", "AB-12-design-feature-skill"),
            ("the slug leaves room for the key", "AB-12\n" + "w" * 300,
             "AB-12-" + "w" * 244),
            ("a lowercase key", "ab-12\nx", "ValueError"),
            ("a key holding shell text", "AB-12$(x)\nx", "ValueError"),
            ("no words", "AB-12\n", "ValueError"), ("no key", "\nwords", "ValueError"),
            ("a key at the limit", "A" * 61 + "-12\nx", "A" * 61 + "-12-x"),
            ("a key over the limit", "A" * 62 + "-12\nx", "ValueError")]:
        failures += report("ticket_branch", name, result_of(ticket_branch, text), expected)
    failures += report("ticket_branch", "a key outside the prefix",
                       result_of(ticket_branch, "XY-1\nwords", "AB"), "ValueError")
    for name, key, expected in [
            ("an underscore project key", "AB_X-1", True), ("a digit in the project", "A2-1", True),
            ("a one-letter project", "A-1", False), ("issue zero", "AB-0", False),
            ("a leading zero", "AB-012", False), ("lowercase", "ab-1", False),
            ("no number", "AB-", False), ("trailing text", "AB-1x", False)]:
        failures += report("JIRA_KEY", name, bool(re.fullmatch(JIRA_KEY, key)), expected)
    failures += report("ticket_branch", "an underscore project key with no prefix",
                       result_of(ticket_branch, "AB_X-1\nwords"), "AB_X-1-words")
    failures += report("ticket_branch", "a malformed prefix",
                       result_of(ticket_branch, "AB-1\nwords", ""), "ValueError")
    for name, text, prefix, expected in [
            ("one key", "AB-12\n", "AB", "AB-12"),
            ("a second line", "AB-12\nmore words", "AB", "ValueError"),
            ("trailing words", "AB-12 words", None, "ValueError"),
            ("a key outside the prefix", "XY-1", "AB", "ValueError"),
            ("a malformed prefix", "AB-1", "a", "ValueError")]:
        failures += report("ticket_key", name, result_of(ticket_key, text, prefix), expected)
    failures += report("ticket_branch", "a key under the prefix",
                       result_of(ticket_branch, "AB-1\nwords", "AB"), "AB-1-words")
    failures += report("ticket_branch", "a key whose project starts with the prefix",
                       result_of(ticket_branch, "AB_X-1\nwords", "AB"), "ValueError")
    failures += report("ticket_branch", "a key line's spaces and CR are stripped",
                       result_of(ticket_branch, " AB-1 \r\nwords"), "AB-1-words")
    failures += report("ticket_branch", "a one-letter project key", result_of(ticket_branch,
                       "A-1\nwords"), "ValueError")
    for name, stdin, given, expected in [
            ("a given value wins, even empty", "piped\n", "", ""),
            ("trailing newlines are dropped", "a\n\n", None, "a"),
            ("a CRLF line ending is dropped", "1.2.0\r\n", None, "1.2.0"),
            ("a newline inside is kept", "a\nb\n", None, "a\nb"),
            ("a terminal is refused, never read", None, None,
             "no value was given, and standard input is a terminal")]:
        class Input(io.StringIO):
            def isatty(self, terminal=stdin is None):
                return terminal
        saved, sys.stdin = sys.stdin, Input(stdin or "")
        try:
            got = result_or_message(lambda: text_input(given))
        finally:
            sys.stdin = saved
        failures += report("text_input", name, got, expected)
    failures += cli_case(this, "ticket-branch reads standard input", ["ticket-branch"],
                         "AB-12-design-feature-skill", 0, input="AB-12\nDesign feature skill\n")
    failures += cli_case(this, "a malformed key is invalid", ["ticket-branch", "--prefix", "AB"],
                         "INVALID:", 1, input="ab-12\nx\n")
    failures += cli_case(this, "draft-slug fits the readback copy", ["draft-slug"], "d" * 187, 0,
                         input="d" * 300 + "\n", exact=True)
    failures += cli_case(this, "ticket-key prints a key under the prefix",
                         ["ticket-key", "--prefix", "AB"], "AB-12", 0, input="AB-12\n", exact=True)
    failures += cli_case(this, "a ticket-key holding shell text is invalid", ["ticket-key"],
                         "INVALID:", 1, input="AB-12$(x)\n")
    failures += cli_case(this, "ticket-keys lists each key under the prefix once",
                         ["ticket-keys", "--prefix", "AB"], "AB-12\nAB-3", 0,
                         input="AB-12 - x\nAB-3 and XY-1, AB-12 again, AB_C-4, _AB-5, 1AB-6\n",
                         exact=True)
    for name, path, expected, status in [
            ("design-path prints a design under --dir", "docs/design/x.md", "docs/design/x.md", 0),
            ("a second line is invalid", "docs/design/x.md\ndocs/design/y.md", "INVALID:", 1),
            ("a '..' component is invalid", "docs/design/../x.md", "INVALID:", 1),
            ("a '.' component is invalid", "docs/design/./x.md", "INVALID:", 1),
            ("an empty component is invalid", "docs/design//x.md", "INVALID:", 1),
            ("a path outside --dir is invalid", "docs/designs/x.md", "INVALID:", 1),
            ("a path that is not .md is invalid", "docs/design/x.txt", "INVALID:", 1),
            ("a bare .md under --dir is invalid", "docs/design/.md", "INVALID:", 1),
            ("a ref prefix is invalid", "HEAD:docs/design/x.md", "INVALID:", 1),
            ("a nested path is invalid", "docs/design/sub/x.md", "INVALID:", 1),
            ("a nested bare .md is invalid", "docs/design/sub/.md", "INVALID:", 1),
            ("a name that is no slug is invalid", "docs/design/-x.md", "INVALID:", 1),
            ("an uppercase name is invalid", "docs/design/X.md", "INVALID:", 1)]:
        failures += cli_case(this, name, ["design-path", "--dir", "docs/design"], expected,
                             status, input=f"{path}\n", exact=status == 0)
    failures += cli_case(this, "design-path without --dir is usage", ["design-path"], "", 2,
                         input="docs/design/x.md\n")
    failures += cli_case(this, "an ADR path prints under its --dir",
                         ["design-path", "--dir", "docs/adr", "--key", "adr_dir"],
                         "docs/adr/0001-use-location.md", 0,
                         input="docs/adr/0001-use-location.md\n", exact=True)
    failures += cli_case(this, "an invalid --dir is invalid", ["design-path", "--dir", "../d"],
                         "INVALID:", 1, input="../d/x.md\n")
    failures += cli_case(this, "a trailing slash on --dir is the same directory",
                         ["design-path", "--dir", "docs/design/"], "docs/design/x.md", 0,
                         input="docs/design/x.md\n", exact=True)
    failures += cli_case(this, "an invalid ADR --dir names adr_dir",
                         ["design-path", "--dir", "../adr", "--key", "adr_dir"],
                         "INVALID: adr_dir", 1, input="../adr/0001-x.md\n")
    failures += cli_case(this, "an ADR path outside its --dir names adr_dir",
                         ["design-path", "--dir", "docs/adr", "--key", "adr_dir"],
                         "INVALID: path 'docs/design/x.md' is not directly under adr_dir", 1,
                         input="docs/design/x.md\n")
    failures += cli_case(this, "an empty --dir component names design_dir",
                         ["design-path", "--dir", "docs//design"], "INVALID: design_dir", 1,
                         input="docs/design/x.md\n")
    failures += cli_case(this, "no subcommand is usage", [], "", 2)
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("slug").add_argument("--title")
    commands.add_parser("pr-number")
    commands.add_parser("ticket-branch").add_argument("--prefix")
    commands.add_parser("draft-slug")
    commands.add_parser("ticket-key").add_argument("--prefix")
    commands.add_parser("ticket-keys").add_argument("--prefix", required=True)
    design = commands.add_parser("design-path")
    design.add_argument("--dir", required=True)
    design.add_argument("--key", choices=("design_dir", "adr_dir"), default="design_dir")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return run_check(parser, {"slug": lambda: slug_of(text_input(args.title)),
                              "pr-number": lambda: pr_number(text_input(None)),
                              "ticket-branch": lambda: ticket_branch(text_input(None),
                                                                     args.prefix),
                              "draft-slug": lambda: slug_of(text_input(None), DRAFT_SLUG_MAX),
                              "ticket-key": lambda: ticket_key(text_input(None), args.prefix),
                              "ticket-keys": lambda: ticket_keys(text_input(None),
                                                                 args.prefix),
                              "design-path": lambda: design_path(text_input(None), args.dir,
                                                                 args.key)},
                     args.command)


if __name__ == "__main__":
    sys.exit(main())
