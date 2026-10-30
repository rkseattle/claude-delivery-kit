"""The project.json rules, the record-parsing rules, the check-script entry point, and the
self-test helpers, the kit's release, review, incident, maintenance, retirement, and design
scripts share. Standard library only, except fence_split and markdown_tokens, which load the
CommonMark parser vendored beside the README checker, and front_matter, the maintenance
check, and scripts/ci/actions-pinned.sh, which load YAML_VENDOR's PyYAML.

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
run by skills/plan-project/SKILL.md for its slug and its brief's path,
skills/write-tickets/SKILL.md for its draft's, a design's path and read, the brief's read,
and the design's Epic key, skills/plan-work/SKILL.md for a design's and its ADRs' paths,
reads, and statuses,
skills/implement-phases/SKILL.md for its branch, skills/ci-green/SKILL.md for its PR number,
skills/design-feature/SKILL.md for its Epic key, the brief's read, and a design's status
transition, skills/design-feature/SKILL.md and skills/write-tickets/SKILL.md for a
feature's lifecycle state,
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
    project_rules.py design-read --ref REF --config FILE [--key KEY] [--path | --status]
                                   the design, or with --key adr_dir the ADR, at the path
                                   on standard input in REF of FILE's repository, when the
                                   path lies directly under KEY's directory in FILE,
                                   design_dir by default, as `<slug>.md` or an ADR_RECORD
                                   name with no empty, `.`, or `..` component, names a
                                   regular file, and a design's front matter `status` is
                                   `accepted`; with --path, the checked path instead; with
                                   --status, its front matter `status`, unjudged;
                                   INVALID otherwise: KEY unset, design_dir or adr_dir
                                   invalid, or the two naming one directory
    project_rules.py design-transition --ref REF --config FILE
                                   `ok <old> -> <new>` when the design at the path on standard
                                   input, checked as design-read checks it, moves from its
                                   status in REF, `none` when REF lacks it, to its
                                   working-tree status by a move gates/design-exit.md
                                   allows: unchanged, a draft's first `proposed`, or, with
                                   design/<slug> or design/<slug>-rev<N> checked out, a
                                   decision or the reopen `accepted -> proposed`; INVALID
                                   otherwise, naming the move and the branch
    project_rules.py front-matter-status --file PATH --config FILE
                                   the status of the working-tree record at PATH, relative
                                   to FILE's project: its front matter `status`, or, written
                                   before front matter, its `## Decision` read as
                                   legacy_status reads it: `none` for a draft, `undecided`
                                   for a Decision it cannot read; INVALID for a PATH failing
                                   the path check or no regular file reached through no
                                   symlink, text that is not UTF-8, a record with neither
                                   front matter nor a `# ` title, or front matter that is
                                   unreadable or has no text status
    project_rules.py lifecycle --ref REF --config FILE [--epic]
                                   where the feature whose design path, or with --epic whose
                                   Epic key, is on standard input stands: one line naming one
                                   of LIFECYCLE_STATES and a detail, then `NEXT: <command>`,
                                   read offline from REF, the parent's remote ref, the
                                   working tree, design branches, design-feature's Step 6
                                   state, and write-tickets' draft; INVALID for a bad path,
                                   key, or design_dir
    project_rules.py brief-read --config FILE [--path]
                                   the brief that FILE's brief_file names, from the
                                   working tree, when its front matter `status` is
                                   `accepted`, or, written before 1.3.0 with no front
                                   matter, its `## Decision` opens `Approved by`, warned
                                   as deprecated; with --path, brief_file printed back once
                                   it passes the key's check, the file unread; INVALID
                                   otherwise, naming the reason
    A design-read or brief-read refusal of a record's status or presence adds a
    `NEXT: <command>` line after its INVALID line: the skill that moves the record on.
    project_rules.py --self-test   runs the key registry's own cases and those of JIRA_KEY,
                                   slug_of, pr_number, ticket_branch, text_input, run_check,
                                   collected_errors, cli_case, write_scratch, and each
                                   subcommand; exit 0 only if each one matches

"""
import argparse
import ast
import contextlib
import datetime
import functools
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
# A file key's path, as REPO_PATH but allowed a leading `.`, as `.github/brief.md` worked
# unquoted in 1.2.0; a leading `-`, a space, and every shell metacharacter stay refused.
REPO_FILE = re.compile(r"^[A-Za-z0-9_.][A-Za-z0-9._/-]*$")
DISCIPLINES = ("security", "data-ml", "mobile", "embedded", "sre")
DECIMAL = r"-?\d+(?:\.\d+)?"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# A decision record's file name, its number first: design-exit writes `NNNN-<title>.md`, and
# readers take any number and title, as adr-tools lists `[0-9]*-*.md`.
ADR_RECORD = re.compile(r"^(\d+)-[^/]+\.md$")


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


def project_root(config_path):
    """The project a project.json belongs to: the folder holding its `.claude/`, which every
    path key is relative to, as git resolves a pathspec from the working directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(config_path)))


def json_text(text, where):
    """text parsed as JSON, or ValueError naming where, when it is not JSON or nests past
    what Python's decoder can read: the json module has no depth limit to set, so its
    RecursionError is the refusal, turned into the ValueError every check prints."""
    try:
        return json.loads(text)
    except ValueError as error:
        raise ValueError(f"{where}: not JSON: {error}")
    except RecursionError:
        raise ValueError(f"{where}: not JSON: it nests too deeply")


def read_config(config_path):
    """project.json as a dict, or raise ValueError naming what is wrong."""
    try:
        with open(config_path, encoding="utf-8") as handle:
            text = handle.read()
        config = json_text(text, "project.json")
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


def check_repo_path(key, value, pattern=REPO_PATH, first="letter, digit, or '_'"):
    """A directory or file key written unquoted into commands: set, relative, inside the repository
    and outside any .git, made only of characters no shell treats specially. As git's
    verify_path does, it rejects an empty, `.`, or `..` component, trailing slashes aside, and
    a .git component anywhere in the path, case-insensitively and with trailing dots dropped,
    since a case-insensitive disk reads .GIT as .git, Windows reads .git. as .git, and git
    tracks nothing under one."""
    parts = value.rstrip("/").split("/") if isinstance(value, str) else []
    if (is_unset(value) or not isinstance(value, str) or not pattern.fullmatch(value)
            or os.path.isabs(value) or any(part in ("", ".", "..") for part in parts)
            or any(part.rstrip(".").casefold() == ".git" for part in parts)):
        raise ValueError(f"{key} {value!r} is not a relative path inside the repository with no "
                         "empty, '.', or '..' component, no '.git' component in any case "
                         f"with or without trailing dots, starting with a {first}, and made "
                         "only of letters, digits, '.', '_', '-', and '/'")


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
    """path, as check_repo_path judges one repository path, of the form `<directory>/<slug>.md`,
    SLUG's slug, as design-feature names its design docs, or under adr_dir `<directory>/<an
    ADR_RECORD name>`; directory, the value of key, is checked by check_repo_path as the key
    registry checks it. A directory written with a trailing slash yields `<directory>/<name>`
    with a doubled slash when a template joins them, so that one join is read as single, as
    os.path.join reads it. ValueError otherwise, naming key for a bad directory. design_read
    checks a design or ADR path a request or a Jira field names with this before git reads
    it."""
    check_repo_path(key, directory)
    if directory.endswith("/") and path.startswith(directory + "/"):
        path = directory.rstrip("/") + "/" + path[len(directory) + 1:]
    check_repo_path("path", path)
    *parents, name = path.split("/")
    if "/".join(parents) != directory.rstrip("/"):
        raise ValueError(f"path {path!r} is not directly under {key} {directory!r}")
    if key == "adr_dir" and not ADR_RECORD.fullmatch(name):
        raise ValueError(f"path {path!r} does not end in a <number>-<title>.md file name")
    if key != "adr_dir" and (not name.endswith(".md") or
                             not SLUG.fullmatch(name[:-len(".md")])):
        raise ValueError(f"path {path!r} does not end in a <slug>.md file name")
    return path


# The deepest YAML a kit script reads, as Symfony YAML's maxNestingLevel and Suricata cap theirs,
# so the refusal falls at a fixed depth, not wherever Python's stack runs out.
YAML_MAX_DEPTH = 128


@functools.lru_cache(maxsize=None)
def depth_capped_loader():
    """PyYAML's SafeLoader refusing a document nested past YAML_MAX_DEPTH with a YAMLError
    saying it nests too deeply, the one loader every kit script reads YAML through."""
    vendored(YAML_VENDOR)
    import yaml

    class DepthCapped(yaml.SafeLoader):
        depth = 0

        def compose_node(self, parent, index):
            self.depth += 1
            try:
                if self.depth > YAML_MAX_DEPTH:
                    raise yaml.composer.ComposerError(None, None, "nests too deeply",
                                                      self.peek_event().start_mark)
                return super().compose_node(parent, index)
            finally:
                self.depth -= 1

    return DepthCapped


def front_matter(text):
    """The YAML mapping between a document's opening `---` line and the next `---` or `...`
    line, trailing whitespace and a leading byte-order mark allowed, as Jekyll delimits
    front matter. A key written twice in one mapping, `<<` included, is refused, as YAML 1.2
    requires keys to be unique and PyYAML alone keeps the last; a key a merge supplies may
    be overridden, as YAML's merge type allows. ValueError when there is no closed block,
    or it is not YAML or not a mapping."""
    lines = text.lstrip("\ufeff").splitlines(keepends=True)
    if not lines or lines[0].rstrip() != "---":
        raise ValueError("no front matter")
    end = next((index for index, line in enumerate(lines[1:], 1)
                if line.rstrip() in ("---", "...")), None)
    if end is None:
        raise ValueError("front matter is not closed")
    loader = depth_capped_loader()
    import yaml

    class UniqueKeys(loader):
        def construct_mapping(self, node, deep=False):
            keys = [(key.tag, key.value) if isinstance(key, yaml.ScalarNode)
                    else self.construct_object(key, deep=True) for key, _ in node.value]
            if any(keys.count(key) > 1 for key in keys):
                raise yaml.constructor.ConstructorError(None, None, "a key is repeated",
                                                        node.start_mark)
            return super().construct_mapping(node, deep)

    try:
        mapping = yaml.load("".join(lines[1:end]), Loader=UniqueKeys)
    except yaml.YAMLError as error:
        raise ValueError(f"front matter is not YAML ({getattr(error, 'problem', None) or error})")
    if not isinstance(mapping, dict):
        raise ValueError("front matter is not a mapping")
    return mapping


def front_matter_status(path, config):
    """The status of the working-tree record at path, relative to project_root(config) and
    built by the caller from checked values, so a skill reads whether a draft is decided
    from this script, not by eye: its front matter
    `status`, or for a record written before front matter, what legacy_status reads from its
    `## Decision`. ValueError for front matter that is
    unreadable or has no text status, or a path that is no regular file reached through no
    symlink, as brief_read requires."""
    path = re.sub(r"/{2,}", "/", path)
    check_repo_path("path", path, REPO_FILE, "letter, digit, '_', or '.'")
    full = os.path.join(os.path.realpath(project_root(config)), path)
    return record_status(regular_text(full, repr(path)), repr(path))


def record_status(text, where):
    """A record's status by one rule wherever it is read: legacy_status for one opening on
    its `# ` title, as written before front matter, else status_of."""
    first = next((line for line in text.lstrip("\ufeff").splitlines() if line.strip()), "")
    if first.startswith("# "):
        return legacy_status(text)
    return status_of(text, where)


def design_dirs(config):
    """{design_dir, adr_dir} from a project.json dict, each valid or None, and never one
    directory, since a file under it could be read as either: the one rule design_check's
    dirs, design_read, and adr_numbers apply. ValueError naming the problem otherwise."""
    keys = read_keys(config, [OptionalKey("design_dir", None), OptionalKey("adr_dir", None)])
    if None not in keys.values() and \
            len({value.rstrip("/").casefold() for value in keys.values()}) == 1:
        raise ValueError("adr_dir and design_dir name one directory, so no read can tell an "
                         "ADR from a design")
    return keys


class Absent(ValueError):
    """ref_record's error for a checked path its ref does not hold, so a caller to whom a
    missing design is a state, not a failure, tells the two apart, and reads the path."""
    def __init__(self, path, ref):
        super().__init__(f"{path!r} is absent from {ref}")
        self.path = path


def design_read(path, ref, config, key="design_dir", path_only=False, status_only=False):
    """The text of the design, or with key adr_dir the ADR, at path in ref: path lies under
    the directory key holds in config, the project.json the calling skill read, so a key and
    its directory cannot disagree, with design_dir and adr_dir both valid or unset and never
    one directory, since a file under it could be read as either. design_path checks the
    path, and git reads it from ref, relative to project_root(config) as adr_numbers reads
    adr_dir, as a regular file, never a tree, symlink, or submodule; a design's front matter
    `status` must be `accepted`, the MADR status gates/design-exit.md gives an approved
    design. ValueError otherwise, saying which. With status_only, the front matter `status`
    as text, unjudged, so a caller asks this reader whether an ADR is accepted rather than
    reading it by eye. With path_only, the checked path instead of
    the text, printed back as git check-ref-format --normalize prints a ref, so a caller
    uses only the checked value. One reader for write-tickets and plan-work, as kepval is
    one checker of a KEP's status for every consumer."""
    if status_only and path_only:
        raise ValueError("design_read prints the path or the status, not both")
    try:
        path, text = ref_record(path, ref, config, key)
    except Absent as absent:
        if key == "adr_dir":
            raise
        raise Refusal(str(absent), f"/delivery-kit:design-feature {absent.path}")
    if status_only:
        return status_of(text, f"{path!r} in {ref}")
    if key != "adr_dir":
        approved_text(text, f"{path!r} in {ref}", {
            None: f"/delivery-kit:design-feature {path}",
            "rejected": "none — a rejected design is the record of a stop; a new request "
                        "starts a new design"})
    return path if path_only else text


def ref_record(path, ref, config, key="design_dir"):
    """(checked path, text) of the record at path in ref, read as design_read describes;
    Absent when ref lacks it, ValueError for any other failure."""
    root = project_root(config)
    directory = design_dirs(read_config(config))[key]
    if directory is None:
        raise ValueError(f"{key} is unset in project.json")
    path = design_path(path, directory, key)
    try:
        commit = run_git(root, "rev-parse", "--verify", "--end-of-options",
                         f"{ref}^{{commit}}").strip()
    except ValueError as error:
        raise ValueError(f"ref {ref!r} does not name a commit ({error})")
    entry = run_git(root, "ls-tree", "-z", commit, "--", path).rstrip("\0")
    if not entry:
        raise Absent(path, ref)
    mode, kind, blob = entry.split("\t", 1)[0].split()
    if kind != "blob" or mode not in ("100644", "100755"):
        raise ValueError(f"{path!r} in {ref} is not a regular file")
    try:
        text = run_git(root, "cat-file", "blob", blob, text=False).decode("utf8")
    except UnicodeDecodeError:
        raise ValueError(f"{path!r} in {ref} is not UTF-8 text")
    return path, text


def design_branch(slug):
    """design/<slug>, or a reopen's design/<slug>-rev<N> with N from 2, as
    gates/design-exit.md's Status transitions section names them: the one pattern
    design_transition and lifecycle match a design's branches with."""
    return re.compile(rf"design/{re.escape(slug)}(?:-rev(?:[2-9]|[1-9][0-9]+))?")


def local_branch(name):
    """A branch name with its `origin/` remote prefix removed, as `git push` takes it."""
    return name[len("origin/"):] if name.startswith("origin/") else name


# The status moves gates/design-exit.md's Status transitions section allows, each mapped to
# whether it needs a design branch: a draft's first `proposed` needs none.
DESIGN_TRANSITIONS = {(None, "proposed"): False, (None, "accepted"): True,
                      (None, "rejected"): True, ("proposed", "accepted"): True,
                      ("proposed", "rejected"): True, ("accepted", "proposed"): True}


def design_transition(path, ref, config):
    """`ok <old> -> <new>` when the move from the design's status in ref, the parent branch,
    to its status in the working tree is one DESIGN_TRANSITIONS allows, both read by
    record_status, `none` for a design ref lacks or a draft not yet given one; an unchanged
    status is always allowed. A move that needs a branch is allowed only with
    `design/<slug>` or `design/<slug>-rev<N>` checked out, so no status changes on the
    parent branch itself. ValueError naming the move otherwise."""
    try:
        path, text = ref_record(path, ref, config)
        old = record_status(text, f"{path!r} in {ref}")
    except Absent as absent:
        path, old = absent.path, None
    new = front_matter_status(path, config)
    old, new = (None if status == "none" else status for status in (old, new))
    shown = f"{old or 'none'} -> {new or 'none'}"
    if old == new or not DESIGN_TRANSITIONS.get((old, new), True):
        return f"ok {shown}"
    if (old, new) not in DESIGN_TRANSITIONS:
        raise ValueError(f"{path!r} moves {shown}, which gates/design-exit.md does not allow")
    slug = path.rsplit("/", 1)[1][:-len(".md")]
    branch = run_git(project_root(config), "branch", "--show-current").strip()
    if not design_branch(slug).fullmatch(branch):
        shown_branch = repr(branch) if branch else "a detached HEAD"
        raise ValueError(f"{path!r} moves {shown} on {shown_branch}, not on design/{slug} or "
                         f"design/{slug}-rev<N>")
    return f"ok {shown}"


# write-tickets' drafts, where lifecycle reads a design's tickets.
TICKET_DRAFTS = "docs/tickets"
DESIGN_REWORK = re.compile(r"<!-- design-rework: (.+?) @ ([0-9a-f]{40,64}) -->")
REVIEW_ROUND = re.compile(r"<!-- review round ([0-9]+) -->")
TICKETS_CREATED = re.compile(r"^<!-- tickets created -->$", re.M)
LIFECYCLE_STATES = ("no-design", "design-draft", "design-unpushed", "design-in-review",
                    "design-step6-interrupted", "design-rejected", "design-accepted-on-parent",
                    "tickets-draft", "tickets-stalled-needs-design-rework", "tickets-created")


def blob_at(root, revision, path):
    """The blob path names at revision, or "" when revision lacks it."""
    return subprocess.run(["git", "rev-parse", "--verify", "--quiet", "--end-of-options",
                           f"{revision}:{path}"], cwd=root, capture_output=True, text=True,
                          check=False).stdout.strip()


def design_blobs(root, ref, path):
    """Every blob path has held in ref's history, so a branch whose design one of them
    matches was merged, by merge, squash, or rebase alike."""
    return {blob_at(root, commit, path)
            for commit in run_git(root, "rev-list", ref, "--", path).split()} - {""}


def branch_design(root, branch, path):
    """(blob, text) of path at branch, or None when branch lacks it."""
    blob = blob_at(root, branch, path)
    if not blob:
        return None
    try:
        return blob, run_git(root, "cat-file", "blob", blob, text=False).decode("utf8")
    except UnicodeDecodeError:
        raise ValueError(f"{path!r} in {branch} is not UTF-8 text")


def regular_text(full, where):
    """The UTF-8 text of the regular file at full, reached through no symlink: the one read
    of a project file front_matter_status, brief_read, and lifecycle share. ValueError
    naming where otherwise; a folder scan catches it to skip the file."""
    if os.path.realpath(full) != os.path.normpath(full) or not os.path.isfile(full):
        raise ValueError(f"{where} is not a regular file reached through no symlink")
    try:
        with open(full, encoding="utf-8") as handle:
            return handle.read()
    except UnicodeDecodeError:
        raise ValueError(f"{where} is not UTF-8 text")


def scanned_text(full):
    """regular_text, or None for a file a folder scan skips."""
    try:
        return regular_text(full, repr(full))
    except ValueError:
        return None


def checked_design(directory, name):
    """`<directory>/<name>` when design_path accepts it, else None."""
    try:
        return design_path(f"{directory.rstrip('/')}/{name}", directory)
    except ValueError:
        return None


def epic_design(root, directory, ref, key):
    """The design path, as design_path checks one, whose `Epic: <key>` line names key: on
    ref first, then in the working tree, then on a local design branch; None when no design
    names it. A file design_path refuses, a symlink, or text that is not UTF-8 is skipped."""
    line = re.compile(rf"^Epic: {re.escape(key)}\s*$", re.M)
    folder = os.path.join(root, directory)
    for source in [ref, None, *run_git(root, "for-each-ref", "--format=%(refname:short)",
                                       "refs/heads/design/").split()]:
        if source is None:
            names = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
        else:
            names = subprocess.run(["git", "ls-tree", "-z", "--name-only", "--end-of-options",
                                    f"{source}:{directory.rstrip('/')}"], cwd=root,
                                   capture_output=True, check=False).stdout.split(b"\0")
            names = [os.fsdecode(name) for name in names]
        for path in filter(None, (checked_design(directory, name) for name in names)):
            if source is None:
                text = scanned_text(os.path.join(root, path))
            else:
                try:
                    found = branch_design(root, source, path)
                except ValueError:
                    found = None
                text = found[1] if found else None
            if text is not None and line.search(text):
                return path
    return None


def tickets_state(root, path, blob):
    """The tickets lifecycle state of the accepted design at path whose parent blob is blob,
    from the write-tickets draft whose `- Design:` line names it: (state, detail).
    `tickets-created` needs the line write-tickets' Step 8 writes once every ticket is
    created or updated, as git's sequencer marks a finished step, since `Jira:` and
    `Baseline:` are filled on a fetched ticket before Step 8 touches it."""
    folder = os.path.join(root, TICKET_DRAFTS)
    design_line = re.compile(rf"^- Design: `{re.escape(path)}`\s*$", re.M)
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if name.count(".") != 1 or not name.endswith(".md"):
            continue
        draft = scanned_text(os.path.join(folder, name))
        if draft is None or not design_line.search(draft):
            continue
        where = f"{TICKET_DRAFTS}/{name}"
        stalled = [match.group(1) for match in DESIGN_REWORK.finditer(draft)
                   if match.group(2) == blob]
        if stalled:
            return "tickets-stalled-needs-design-rework", f"{where}: {stalled[-1]}"
        if TICKETS_CREATED.search(draft):
            handoff = re.search(r"^Handoff:[ \t]*(\S+)", draft, re.M)
            return "tickets-created", handoff.group(1) if handoff else ""
        rounds = list(REVIEW_ROUND.finditer(draft))
        if not rounds:
            return "tickets-draft", f"{where}: not yet reviewed"
        last = draft[rounds[-1].end():]
        blockers = sum(len(re.findall(r"^- ", section, re.M)) for section in
                       re.findall(r"^### BLOCKER\n(.*?)(?=^#|\Z)", last, re.M | re.S))
        return "tickets-draft", (f"{where}: review round {rounds[-1].group(1)}, "
                                 f"{blockers} BLOCKER{'' if blockers == 1 else 's'}")
    return None


def lifecycle(text, ref, config, epic=False):
    """Where one feature stands, as git status names a repository's state: one state of
    LIFECYCLE_STATES, a detail, and the single command that moves it on, read offline from
    the design at the path on standard input, or with epic the design whose `Epic:` line
    names the key there; ref is the parent branch's remote ref. Jira is the skill's to add.
    ValueError for a bad path, key, directory, or ref, or a parent design not UTF-8."""
    root = os.path.realpath(project_root(config))
    directory = design_dirs(read_config(config))["design_dir"]
    if directory is None:
        raise ValueError("design_dir is unset in project.json")
    try:
        run_git(root, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")
    except ValueError as error:
        raise ValueError(f"ref {ref!r} does not name a commit ({error})")
    key = ticket_key(text) if epic else None
    path = epic_design(root, directory, ref, key) if epic else design_path(text, directory)
    if path is None:
        return [f"no-design no design names {key}", f"NEXT: /delivery-kit:design-feature {key}"]
    slug = path.rsplit("/", 1)[1][:-len(".md")]
    design = f"/delivery-kit:design-feature {key or path}"
    on_ref = branch_design(root, ref, path)
    if on_ref and not key:
        epic_line = re.search(r"^Epic: (" + JIRA_KEY + r")\s*$", on_ref[1], re.M)
        design = f"/delivery-kit:design-feature {epic_line.group(1) if epic_line else path}"
    state_dir = run_git(root, "rev-parse", "--path-format=absolute", "--git-path",
                        "design-feature").strip()
    recorded = scanned_text(os.path.join(state_dir, "slug"))
    if recorded is not None and recorded.strip() == slug:
        return [f"design-step6-interrupted {state_dir}", f"NEXT: {design} (continue or abort)"]
    branch = run_git(root, "branch", "--show-current").strip()
    merged = design_blobs(root, ref, path)
    revisions = [name for name in run_git(root, "for-each-ref", "--format=%(refname:short)",
                                          "refs/heads/design/",
                                          "refs/remotes/origin/design/").split()
                 if design_branch(slug).fullmatch(local_branch(name))]
    parent = local_branch(ref)
    if branch == parent and run_git(root, "rev-list", f"{ref}..HEAD", "--", path).strip():
        taken = {local_branch(name) for name in revisions}
        candidates = itertools.chain([] if on_ref else [f"design/{slug}"],
                                     (f"design/{slug}-rev{n}" for n in itertools.count(2)))
        target = next(name for name in candidates if name not in taken)
        return [f"design-unpushed {branch} is ahead of {ref} on {path}",
                f"NEXT: git switch -c {target} && git branch -f {parent} {ref}"]
    open_revisions = []
    for name in revisions:
        found = branch_design(root, name, path)
        if found and found[0] not in merged:
            open_revisions.append((name, record_status(found[1], f"{path!r} in {name}")))
    for name, status in open_revisions:
        if status in ("proposed", "none"):
            return [f"design-draft {path} on {name}", f"NEXT: {design}"]
    if open_revisions:
        name = open_revisions[0][0]
        return [f"design-in-review {path} on {name}",
                f"NEXT: git push -u origin {local_branch(name)}, then merge its pull request"]
    status = record_status(on_ref[1], f"{path!r} in {ref}") if on_ref else None
    if status is None or status == "none":
        if not os.path.isfile(os.path.join(root, path)):
            return [f"no-design {path} does not exist", f"NEXT: {design}"]
        return [f"design-draft {path} in the working tree", f"NEXT: {design}"]
    if status == "proposed":
        return [f"design-draft {path} is proposed on {ref}, reopened there by hand",
                f"NEXT: {design}"]
    if status == "rejected":
        return [f"design-rejected {path} on {ref}",
                "NEXT: none — a rejected design is the record of a stop; a new request "
                "starts a new design"]
    if status != "accepted":
        raise ValueError(f"{path!r} in {ref} has status {status!r}, which no step writes")
    tickets = tickets_state(root, path, on_ref[0])
    if tickets is None:
        return [f"design-accepted-on-parent {path}",
                f"NEXT: /delivery-kit:write-tickets {path}"]
    state, detail = tickets
    command = {"tickets-stalled-needs-design-rework": design,
               "tickets-created": f"/delivery-kit:plan-work {detail}".rstrip(),
               "tickets-draft": f"/delivery-kit:write-tickets {path}"}[state]
    return [f"{state} {detail}".rstrip(), f"NEXT: {command}"]


def status_of(text, where):
    """The front matter `status` of text, as text; ValueError naming where when the front
    matter is missing or unreadable or its status is absent or not text. The one read of a
    record's status for approved_text, design_read, and front_matter_status."""
    try:
        status = front_matter(text).get("status")
    except ValueError as error:
        raise ValueError(f"{where}: {error}")
    if not isinstance(status, str):
        raise ValueError(f"{where} has no text status ({status!r})")
    return status


class Refusal(ValueError):
    """A refusal that knows the command moving its record on, which run_check prints as a
    `NEXT:` line after the `INVALID:` one, as git status prints how to continue."""
    def __init__(self, message, next_step):
        super().__init__(message)
        self.next_step = next_step


def approved_text(text, where, next_steps=None):
    """text when its front matter `status` is `accepted`, the MADR status a decided record
    carries, so a design and a brief share one definition of approved; a Refusal naming
    where and the status otherwise, its next step next_steps' entry for that status, or for
    None when it has none."""
    next_steps = next_steps or {}
    try:
        status = status_of(text, where)
    except ValueError as error:
        raise Refusal(str(error), next_steps.get(None))
    if status != "accepted":
        raise Refusal(f"{where} has status {status!r}, not 'accepted'",
                      next_steps.get(status, next_steps.get(None)))
    return text


def brief_read(config, path_only=False):
    """The project brief brief_file names in config, read from the project's working tree,
    where plan-project writes it, as a regular file reached through no symlink, when
    approved_text accepts it, the status gates/planning-exit.md's first criterion reads,
    or, for a brief with no front matter, legacy_status does, warned as deprecated. With
    path_only, brief_file printed back once the key registry accepts it and it names no
    folder, the file unread, so plan-project writes only where every reader will look.
    ValueError naming brief_file when it is unset, invalid, or a folder, the file is
    missing, reached through a symlink, or not UTF-8, or it is not approved."""
    path = read_keys(read_config(config), [OptionalKey("brief_file", None)])["brief_file"]
    if path is None:
        raise ValueError("brief_file is unset in project.json")
    if path.endswith("/") or os.path.isdir(os.path.join(project_root(config), path)):
        raise ValueError(f"brief_file {path!r} names a directory, not a file")
    if path_only:
        return path
    root = os.path.realpath(project_root(config))
    full = os.path.join(root, path)
    where = f"brief_file {path!r}"
    try:
        text = regular_text(full, where)
    except ValueError as error:
        if os.path.lexists(full):
            raise
        raise Refusal(str(error), "/delivery-kit:plan-project")
    next_steps = {None: "/delivery-kit:plan-project",
                  "rejected": "none — the sponsor rejected the project"}
    status = legacy_status(text)
    if status in ("accepted", "rejected"):
        print(f"DEPRECATED: {where} records its decision only in ## Decision, as plan-project "
              "wrote it before 1.3.0; add `status`, `date`, and `decision-makers` front "
              "matter, which 1.4.0 will require", file=sys.stderr)
        if status != "accepted":
            raise Refusal(f"{where} has status {status!r}, not 'accepted'",
                          next_steps["rejected"])
        return text
    return approved_text(text, where, next_steps)


# The release that drops legacy_status, as the deprecation library's removed_in names one;
# the self-test fails once plugin.json reaches it with legacy_status still here.
LEGACY_STATUS_REMOVED_IN = (1, 4, 0)


def legacy_status(text):
    """The decision of a brief written before front matter carried its status, as
    plan-project 1.2.0 wrote one: opening on its `# ` title, with no `---` line before its
    one `## Decision` section, read as CommonMark so a fenced, quoted, or listed decoy does
    not count, whose first paragraph opens `Approved by `, `Rejected by `, or `Pending`:
    `accepted`, `rejected`, or `none`, and `none` too with no `## Decision` yet, the draft a
    skill resumes; `undecided` for any other Decision, two of them, one not opening on a
    paragraph, or a `---` line before it; None for a record not opening on its title. Read for one release, as a format is dropped over two."""
    lines = text.lstrip("\ufeff").splitlines()
    first = next((line for line in lines if line.strip()), "")
    if not first.startswith("# "):
        return None
    before = list(itertools.takewhile(lambda line: line.rstrip() != "## Decision", lines))
    if any(line.rstrip() == "---" for line in before):
        return "undecided"
    tokens = markdown_tokens(text)
    decisions = [index for index, token in enumerate(tokens)
                 if (token.type, token.tag, token.level) == ("heading_open", "h2", 0)
                 and tokens[index + 1].content.strip() == "Decision"]
    if not decisions:
        return "none"
    opening = tokens[decisions[0] + 3:decisions[0] + 5] if len(decisions) == 1 else []
    if len(opening) != 2 or opening[0].type != "paragraph_open":
        return "undecided"
    decision = words(opening[1].content)
    return "accepted" if decision.startswith("Approved by ") else \
        "rejected" if decision.startswith("Rejected by ") else \
        "none" if decision.startswith("Pending") else "undecided"


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
    "brief_file": KeyShape(lambda value: check_repo_path("brief_file", value, REPO_FILE,
                                                         "letter, digit, '_', or '.'")),
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
    - a ValueError or OSError raised: `INVALID: <what>` to stderr, then `NEXT: <command>`
      for a Refusal; exit 1
    - no check of that name: usage to stderr; exit 2
    """
    if command not in checks:
        parser.print_usage(sys.stderr)
        return 2
    try:
        result = checks[command]()
    except (ValueError, OSError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        if getattr(error, "next_step", None):
            print(f"NEXT: {error.next_step}", file=sys.stderr)
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


def design_read_self_test(this):
    """design_read over a scratch repository holding an approved design, ones whose front
    matter is absent, malformed, or not `status: accepted`, a tree and a symlink named like
    designs, and an ADR."""
    approved = ("---\nstatus: accepted\ndate: 2026-10-26\ndecision-makers: rob\n---\n\n# X\n\n"
                "## Decision\n\nApproved by rob on 2026-10-26.\n")
    body = "\n# D\n\n## Decision\n\nApproved by rob on 2026-10-26.\n"
    files = {"docs/design/ok.md": approved,
             "docs/design/crlf.md": approved.replace("\n", "\r\n"),
             "docs/design/pending.md": "---\nstatus: proposed\n---\n" + body,
             "docs/design/rejected.md": "---\nstatus: rejected\n---\n" + body,
             "docs/design/capital.md": "---\nstatus: Accepted\n---\n" + body,
             "docs/design/nofront.md": "# N\n\nstatus: accepted\n\n## Decision\n\n"
                                       "Approved by rob.\n",
             "docs/design/late.md": "\n---\nstatus: accepted\n---\n" + body,
             "docs/design/unclosed.md": "---\nstatus: accepted\n" + body,
             "docs/design/listed.md": "---\n- status: accepted\n---\n" + body,
             "docs/design/twice.md": "---\nstatus: proposed\nstatus: accepted\n---\n" + body,
             "docs/design/broken.md": "---\nstatus: [accepted\n---\n" + body,
             "docs/design/nostatus.md": "---\ndate: 2026-10-26\n---\n" + body,
             "docs/design/merged.md": "---\nbase: &b {status: accepted}\n<<: *b\n---\n" + body,
             "docs/design/override.md": "---\nbase: &b {status: proposed}\n<<: *b\n"
                                        "status: accepted\n---\n" + body,
             "docs/design/loose.md": "\ufeff--- \nstatus: accepted\n...\n" + body,
             "docs/design/tree.md/inner.md": approved,
             "docs/adr/0001-a.md": "---\nstatus: accepted\n---\n",
             "docs/adr/0002-Use-X.md": "---\nstatus: accepted\n---\n",
             "sub/docs/design/nested.md": approved}
    config = {"design_dir": "docs/design", "adr_dir": "docs/adr"}
    failures = 0
    with tempfile.TemporaryDirectory() as root, \
            process_state(isolated_git_environment(), root):
        for name, text in files.items():
            write_scratch(root, text, name)
        os.symlink("ok.md", os.path.join(root, "docs/design/link.md"))
        write_scratch(root, b"---\nstatus: accepted\n---\n# L r\xf6b\n", "docs/design/latin.md")
        os.chmod(write_scratch(root, approved, "docs/design/exec.md"), 0o755)
        project = write_scratch(root, config, ".claude/project.json")
        run_git(root, "init", "--quiet", "--initial-branch=main")
        run_git(root, "add", "-A")
        run_git(root, "update-index", "--add", "--cacheinfo",
                f"160000,{'1' * 40},docs/design/module.md")
        run_git(root, "commit", "--quiet", "-m", "designs")
        for name, path, adr, expected in [
                ("an approved design is read", "docs/design/ok.md", False, approved),
                ("a CRLF design is read", "docs/design/crlf.md", False,
                 files["docs/design/crlf.md"]),
                ("a proposed design is invalid", "docs/design/pending.md", False,
                 "status 'proposed', not 'accepted'"),
                ("a rejected design is invalid", "docs/design/rejected.md", False,
                 "status 'rejected', not 'accepted'"),
                ("a capitalized status is invalid", "docs/design/capital.md", False,
                 "status 'Accepted', not 'accepted'"),
                ("a status line in the body is no front matter", "docs/design/nofront.md",
                 False, "no front matter"),
                ("front matter after a blank line is none", "docs/design/late.md", False,
                 "no front matter"),
                ("unclosed front matter is invalid", "docs/design/unclosed.md", False,
                 "front matter is not closed"),
                ("a list as front matter is invalid", "docs/design/listed.md", False,
                 "front matter is not a mapping"),
                ("a repeated status key is invalid", "docs/design/twice.md", False,
                 "a key is repeated"),
                ("front matter that is not YAML is invalid", "docs/design/broken.md", False,
                 "front matter is not YAML ("),
                ("front matter with no status is invalid", "docs/design/nostatus.md", False,
                 "has no text status (None)"),
                ("a status from a merge key is read", "docs/design/merged.md", False,
                 files["docs/design/merged.md"]),
                ("an explicit status overrides a merged one", "docs/design/override.md", False,
                 files["docs/design/override.md"]),
                ("a BOM, a padded opener, and a '...' closer are read", "docs/design/loose.md",
                 False, files["docs/design/loose.md"]),
                ("an executable design is read", "docs/design/exec.md", False, approved),
                ("a missing design is invalid", "docs/design/gone.md", False, "absent"),
                ("a tree named like a design is invalid", "docs/design/tree.md", False,
                 "not a regular file"),
                ("a symlink named like a design is invalid", "docs/design/link.md", False,
                 "not a regular file"),
                ("a design that is not UTF-8 is invalid", "docs/design/latin.md", False,
                 "not UTF-8"),
                ("a submodule named like a design is invalid", "docs/design/module.md", False,
                 "not a regular file"),
                ("an ADR is read without a status check", "docs/adr/0001-a.md", True,
                 files["docs/adr/0001-a.md"]),
                ("an ADR with an uppercase title is read", "docs/adr/0002-Use-X.md", True,
                 files["docs/adr/0002-Use-X.md"]),
                ("an ADR with no number is invalid", "docs/adr/use-x.md", True,
                 "<number>-<title>.md"),
                ("a design path read as an ADR is invalid", "docs/design/pending.md", True,
                 "not directly under adr_dir")]:
            key = "adr_dir" if adr else "design_dir"
            got = result_or_message(lambda: design_read(path, "main", project, key))
            read = expected in files.values()
            failures += report("design_read", name, got == expected if read else
                               expected in got and got not in files.values(), True)
        failures += report("design_read", "an unknown ref is named",
                           result_or_message(lambda: design_read(
                               "docs/design/ok.md", "nope", project)).startswith(
                               "ref 'nope' does not name a commit (git rev-parse failed: fatal:"),
                           True)
        adr_read = ("docs/adr/0001-a.md", "adr_dir")
        approved_design_read = ("docs/design/ok.md", "design_dir")
        for name, setting, read, expected in [
                ("an unset adr_dir is named", {"design_dir": "docs/design"}, adr_read,
                 "adr_dir is unset"),
                ("an invalid adr_dir is named", dict(config, adr_dir="../adr"), adr_read,
                 "adr_dir '../adr' is not a relative path"),
                ("an invalid adr_dir is named reading a design", dict(config, adr_dir="../adr"),
                 approved_design_read, "adr_dir '../adr' is not a relative path"),
                ("an invalid design_dir is named reading an ADR",
                 dict(config, design_dir="../design"), adr_read,
                 "design_dir '../design' is not a relative path"),
                ("one directory for designs and ADRs is refused reading an ADR",
                 dict(config, adr_dir="docs/design/"), adr_read,
                 "adr_dir and design_dir name one"),
                ("one directory for designs and ADRs is refused reading a design",
                 dict(config, adr_dir="docs/design"), approved_design_read,
                 "adr_dir and design_dir name one")]:
            write_scratch(root, setting, ".claude/project.json")
            got = result_or_message(lambda: design_read(read[0], "main", project, read[1]))
            failures += report("design_read", name, got.startswith(expected), True)
        write_scratch(root, config, ".claude/project.json")
        subproject = write_scratch(root, {"design_dir": "docs/design"}, "sub/.claude/project.json")
        failures += report("design_read", "the named project.json is read, not the repository "
                           "top's", result_or_message(lambda: design_read(
                               "docs/adr/0001-a.md", "main", subproject, "adr_dir")),
                           "adr_dir is unset in project.json")
        failures += report("design_read", "a nested project's design is read from its folder",
                           result_or_message(lambda: design_read(
                               "docs/design/nested.md", "main", subproject)), approved)
        failures += report("project_root", "the folder holding .claude/", project_root(subproject),
                           os.path.join(root, "sub"))
        failures += cli_case(this, "design-read prints an approved design",
                             ["design-read", "--ref", "main", "--config", project],
                             approved.strip(), 0, input="docs/design/ok.md\n", cwd=root,
                             env=isolated_git_environment(), exact=True)
        failures += cli_case(this, "design-read from a subdirectory reads from the root",
                             ["design-read", "--ref", "main", "--config", project],
                             approved.strip(), 0, input="docs/design/ok.md\n",
                             cwd=os.path.join(root, "docs"), env=isolated_git_environment(),
                             exact=True)
        failures += cli_case(this, "design-read --key adr_dir reads an ADR",
                             ["design-read", "--ref", "main", "--config", project, "--key",
                              "adr_dir"],
                             files["docs/adr/0001-a.md"].strip(), 0,
                             input="docs/adr/0001-a.md\n", cwd=root,
                             env=isolated_git_environment(), exact=True)
        failures += cli_case(this, "--key adr_dir does not read a design unchecked",
                             ["design-read", "--ref", "main", "--config", project, "--key",
                              "adr_dir"],
                             "INVALID: path 'docs/design/pending.md' is not directly under "
                             "adr_dir", 1, input="docs/design/pending.md\n", cwd=root,
                             env=isolated_git_environment())
        failures += cli_case(this, "design-read has no --dir to name another directory",
                             ["design-read", "--ref", "main", "--config", project, "--key",
                              "adr_dir", "--dir",
                              "docs/design"], "", 2, input="docs/design/pending.md\n",
                             cwd=root, env=isolated_git_environment())
        write_scratch(root, dict(config, design_dir="docs/design/"), ".claude/project.json")
        failures += cli_case(this, "design-read --path prints the checked path, one slash",
                             ["design-read", "--ref", "main", "--config", project, "--path"],
                             "docs/design/ok.md", 0, input="docs/design//ok.md\n", cwd=root,
                             env=isolated_git_environment(), exact=True)
        failures += cli_case(this, "design-read names design-feature for a proposed design",
                             ["design-read", "--ref", "main", "--config", project],
                             "NEXT: /delivery-kit:design-feature docs/design/pending.md", 1,
                             line=1, stderr_prefixes=("NEXT",), input="docs/design/pending.md\n",
                             cwd=root, env=isolated_git_environment(), exact=True)
        failures += cli_case(this, "design-read names no next step for a rejected design",
                             ["design-read", "--ref", "main", "--config", project],
                             "NEXT: none — a rejected design", 1, line=1,
                             stderr_prefixes=("NEXT",), input="docs/design/rejected.md\n",
                             cwd=root, env=isolated_git_environment())
        failures += cli_case(this, "design-read --path checks the status first",
                             ["design-read", "--ref", "main", "--config", project, "--path"],
                             "INVALID: 'docs/design/pending.md' in main has status 'proposed'",
                             1, input="docs/design/pending.md\n", cwd=root,
                             env=isolated_git_environment())
        write_scratch(root, dict(config, adr_dir="docs/adr/"), ".claude/project.json")
        failures += cli_case(this, "design-read --key adr_dir --status prints its status",
                             ["design-read", "--ref", "main", "--config", project, "--key",
                              "adr_dir", "--status"], "accepted", 0,
                             input="docs/adr/0001-a.md\n", cwd=root,
                             env=isolated_git_environment(), exact=True)
        failures += cli_case(this, "design-read --status names a design with no front matter",
                             ["design-read", "--ref", "main", "--config", project, "--status"],
                             "INVALID: 'docs/design/nofront.md' in main: no front matter", 1,
                             input="docs/design/nofront.md\n", cwd=root,
                             env=isolated_git_environment())
        failures += cli_case(this, "design-read --status names a missing status",
                             ["design-read", "--ref", "main", "--config", project, "--status"],
                             "INVALID: 'docs/design/nostatus.md' in main has no text status", 1,
                             input="docs/design/nostatus.md\n", cwd=root,
                             env=isolated_git_environment())
        failures += cli_case(this, "design-read takes --path or --status, not both",
                             ["design-read", "--ref", "main", "--config", project, "--path",
                              "--status"], "", 2, input="docs/design/ok.md\n", cwd=root,
                             env=isolated_git_environment())
        failures += cli_case(this, "design-read --status prints a proposed design's status",
                             ["design-read", "--ref", "main", "--config", project, "--status"],
                             "proposed", 0, input="docs/design/pending.md\n", cwd=root,
                             env=isolated_git_environment(), exact=True)
        failures += cli_case(this, "design-read --key adr_dir --path prints the checked ADR path",
                             ["design-read", "--ref", "main", "--config", project, "--key",
                              "adr_dir", "--path"], "docs/adr/0001-a.md", 0,
                             input="docs/adr//0001-a.md\n", cwd=root,
                             env=isolated_git_environment(), exact=True)
        write_scratch(root, config, ".claude/project.json")
        failures += cli_case(this, "design-read without --config is usage",
                             ["design-read", "--ref", "main"], "", 2,
                             input="docs/design/ok.md\n", cwd=root,
                             env=isolated_git_environment())
        failures += cli_case(this, "design-read without --ref is usage",
                             ["design-read"], "", 2,
                             input="docs/design/ok.md\n", cwd=root,
                             env=isolated_git_environment())
        failures += cli_case(this, "design-read of a second line is invalid",
                             ["design-read", "--ref", "main", "--config", project],
                             "INVALID:", 1, input="docs/design/ok.md\nmain:docs/design/ok.md\n",
                             cwd=root, env=isolated_git_environment())
    with tempfile.TemporaryDirectory() as project:
        accepted = "---\nstatus: accepted\n---\n# B\n"
        config_file = write_scratch(project, {"brief_file": "docs/brief.md"},
                                    ".claude/project.json")
        for name, setting, content, expected in [
                ("an accepted brief is read", None, accepted, accepted),
                ("a proposed brief is refused", None, "---\nstatus: proposed\n---\n# B\n",
                 "brief_file 'docs/brief.md' has status 'proposed', not 'accepted'"),
                ("a rejected brief is refused", None, "---\nstatus: rejected\n---\n# B\n",
                 "brief_file 'docs/brief.md' has status 'rejected', not 'accepted'"),
                ("a pre-1.3.0 brief approved in ## Decision is read", None,
                 "# B\n\n## Decision\nApproved by s on 2026-10-26.\n",
                 "# B\n\n## Decision\nApproved by s on 2026-10-26.\n"),
                ("a pre-1.3.0 brief rejected in ## Decision is rejected", None,
                 "# B\n\n## Decision\nRejected by s on 2026-10-26.\nOut of budget.\n",
                 "brief_file 'docs/brief.md' has status 'rejected', not 'accepted'"),
                ("a pre-1.3.0 brief still Pending is refused", None,
                 "# B\n\n## Decision\nPending — s.\n",
                 "brief_file 'docs/brief.md': no front matter"),
                ("a fenced Approved decoy in a pre-1.3.0 brief is refused", None,
                 "# B\n\n```\n## Decision\nApproved by s on 2026-10-26.\n```\n\n"
                 "## Decision\nPending — s.\n", "brief_file 'docs/brief.md': no front matter"),
                ("a brief_file naming a folder is refused", {"brief_file": "docs"}, accepted,
                 "brief_file 'docs' names a directory"),
                ("a padded opener over a rejected status is refused", None,
                 "--- \nstatus: rejected\n---\n\n## Decision\nApproved by s on 2026-10-26.\n",
                 "brief_file 'docs/brief.md' has status 'rejected'"),
                ("a blank line over a rejected status is refused", None,
                 "\n---\nstatus: rejected\n---\n\n## Decision\nApproved by s on 2026-10-26.\n",
                 "brief_file 'docs/brief.md': no front matter"),
                ("a comment over a proposed status is refused", None,
                 "<!-- x -->\n---\nstatus: proposed\n---\n\n## Decision\nApproved by s.\n",
                 "brief_file 'docs/brief.md': no front matter"),
                ("a tab after the opener over a proposed status is refused", None,
                 "---\t\nstatus: proposed\n---\n\n## Decision\nApproved by s on 2026-10-26.\n",
                 "brief_file 'docs/brief.md' has status 'proposed'"),
                ("a missing brief is refused", None, None,
                 "brief_file 'docs/brief.md' is not a regular file reached through no symlink"),
                ("an unset brief_file is named", {}, accepted, "brief_file is unset"),
                ("an invalid brief_file is named", {"brief_file": "../brief.md"}, accepted,
                 "brief_file '../brief.md' is not a relative path")]:
            brief = os.path.join(project, "docs", "brief.md")
            if os.path.exists(brief):
                os.remove(brief)
            if content is not None:
                write_scratch(project, content, "docs/brief.md")
            write_scratch(project, {"brief_file": "docs/brief.md"} if setting is None
                          else setting, ".claude/project.json")
            warning = io.StringIO()
            with contextlib.redirect_stderr(warning):
                got = result_or_message(lambda: brief_read(config_file))
            read = expected in (accepted, content)
            failures += report("brief_read", f"{name}: a warning only on a legacy read",
                               warning.getvalue().startswith("DEPRECATED: "),
                               content is not None
                               and legacy_status(content) in ("accepted", "rejected"))
            failures += report("brief_read", name, got == expected if read
                               else got.startswith(expected), True)
        write_scratch(project, {"brief_file": "docs/brief.md"}, ".claude/project.json")
        os.remove(os.path.join(project, "docs", "brief.md"))
        write_scratch(project, accepted, "docs/real.md")
        os.symlink("real.md", os.path.join(project, "docs", "brief.md"))
        failures += report("brief_read", "a symlinked brief is refused",
                           result_or_message(lambda: brief_read(config_file)),
                           "brief_file 'docs/brief.md' is not a regular file reached through "
                           "no symlink")
        failures += cli_case(this, "brief-read refuses a symlinked brief",
                             ["brief-read", "--config", config_file],
                             "INVALID: brief_file 'docs/brief.md' is not a regular file", 1)
        failures += cli_case(this, "brief-read names no next step for a symlinked brief",
                             ["brief-read", "--config", config_file], "", 1, line=1,
                             stderr_prefixes=("",), exact=True)
        os.remove(os.path.join(project, "docs", "brief.md"))
        failures += cli_case(this, "brief-read names plan-project for a missing brief",
                             ["brief-read", "--config", config_file],
                             "NEXT: /delivery-kit:plan-project", 1, line=1,
                             stderr_prefixes=("NEXT",), exact=True)
        with tempfile.TemporaryDirectory() as outside:
            write_scratch(outside, accepted, "brief.md")
            os.rename(os.path.join(project, "docs"), os.path.join(project, "real-docs"))
            os.symlink(outside, os.path.join(project, "docs"))
            failures += report("brief_read", "a brief under a symlinked folder is refused",
                               result_or_message(lambda: brief_read(config_file)),
                               "brief_file 'docs/brief.md' is not a regular file reached "
                               "through no symlink")
            os.remove(os.path.join(project, "docs"))
        os.rename(os.path.join(project, "real-docs"), os.path.join(project, "docs"))
        write_scratch(project, b"---\nstatus: accepted\n---\n# B r\xf6b\n", "docs/brief.md")
        failures += report("brief_read", "a brief that is not UTF-8 is refused",
                           result_or_message(lambda: brief_read(config_file)),
                           "brief_file 'docs/brief.md' is not UTF-8 text")
        write_scratch(project, {"brief_file": ".github/brief.md"}, ".claude/project.json")
        failures += report("brief_read", "a leading-dot brief_file, valid in 1.2.0, is kept",
                           brief_read(config_file, True), ".github/brief.md")
        for name, unsafe in [("a space", "docs/project brief.md"), ("a ';'", "docs/b;x.md"),
                             ("a leading '-'", "-all.md")]:
            write_scratch(project, {"brief_file": unsafe}, ".claude/project.json")
            failures += report("brief_read", f"a brief_file with {name}, unsafe unquoted, is "
                               "refused", result_or_message(lambda: brief_read(config_file, True))
                               .startswith(f"brief_file {unsafe!r} is not a relative path"), True)
        write_scratch(project, {"brief_file": "docs/brief.md"}, ".claude/project.json")
        failures += report("brief_read", "--path prints brief_file without reading it",
                           brief_read(config_file, True), "docs/brief.md")
        for name, setting, expected in [
                ("--path refuses a folder", {"brief_file": "docs"},
                 "INVALID: brief_file 'docs' names a directory"),
                ("--path refuses a trailing slash", {"brief_file": "docs/brief.md/"},
                 "INVALID: brief_file 'docs/brief.md/' names a directory"),
                ("--path names an unset brief_file", {}, "INVALID: brief_file is unset"),
                ("--path names an invalid brief_file", {"brief_file": "../brief.md"},
                 "INVALID: brief_file '../brief.md' is not a relative path")]:
            write_scratch(project, setting, ".claude/project.json")
            failures += cli_case(this, f"brief-read {name}",
                                 ["brief-read", "--path", "--config", config_file], expected, 1)
        write_scratch(project, {"brief_file": "docs/brief.md"}, ".claude/project.json")
        os.remove(os.path.join(project, "docs", "brief.md"))
        write_scratch(project, accepted, "docs/brief.md")
        failures += cli_case(this, "brief-read prints an accepted brief",
                             ["brief-read", "--config", config_file], accepted.strip(), 0,
                             exact=True)
        legacy = "# B\n\n## Decision\nApproved by s on 2026-10-26.\n"
        write_scratch(project, legacy, "docs/brief.md")
        failures += cli_case(this, "brief-read prints a pre-1.3.0 approved brief",
                             ["brief-read", "--config", config_file], legacy.strip(), 0,
                             exact=True)
    for name, config, expected in [
            ("two directories are kept", {"design_dir": "d", "adr_dir": "a"},
             {"design_dir": "d", "adr_dir": "a"}),
            ("one directory in two cases is refused",
             {"design_dir": "docs/ADR", "adr_dir": "docs/adr"},
             "adr_dir and design_dir name one directory, so no read can tell an ADR from a "
             "design"),
            ("one directory is refused", {"design_dir": "d", "adr_dir": "d/"},
             "adr_dir and design_dir name one directory, so no read can tell an ADR from a "
             "design"),
            ("unset keys are None", {}, {"design_dir": None, "adr_dir": None}),
            ("an invalid design_dir is named", {"design_dir": "../d"},
             "design_dir '../d' is not a relative path"),
            ("an invalid adr_dir beside a valid design_dir is named",
             {"design_dir": "d", "adr_dir": "/a"}, "adr_dir '/a' is not a relative path")]:
        got = result_or_message(lambda: design_dirs(config))
        failures += report("design_dirs", name, got.startswith(expected)
                           if isinstance(expected, str) and isinstance(got, str) else got,
                           True if isinstance(expected, str) else expected)
    approved = "# B\n\n## Decision\n\nApproved by s on 2026-10-26.\n"
    for name, text, expected in [
            ("an Approved by Decision is accepted", approved, "accepted"),
            ("a Rejected by Decision is rejected", "# B\n\n## Decision\n\nRejected by s.\n",
             "rejected"),
            ("a Pending Decision is none", "# B\n\n## Decision\n\nPending — s.\n", "none"),
            ("two Decision sections are undecided", approved + "\n## Decision\n\nPending.\n",
             "undecided"),
            ("an h3 Decision is no Decision yet", "# B\n\n### Decision\n\nApproved by s.\n",
             "none"),
            ("a quoted Approved by is undecided", "# B\n\n## Decision\n\n> Approved by s.\n",
             "undecided"),
            ("a listed Approved by is undecided", "# B\n\n## Decision\n\n- Approved by s.\n",
             "undecided"),
            ("Approved by in a second paragraph is none",
             "# B\n\n## Decision\n\nPending.\n\nApproved by s.\n", "none"),
            ("a hand-edited Decision is undecided", "# B\n\n## Decision\n\nApproved.\n",
             "undecided"),
            ("no Decision yet is none, a draft", "# B\n\nApproved by s.\n", "none"),
            ("front matter under the title is undecided",
             "# B\n---\nstatus: rejected\n---\n## Decision\nApproved by s.\n", "undecided"),
            ("a thematic break before the Decision is undecided",
             "# B\n\nIntro\n\n---\n\n## Decision\n\nRejected by s.\n", "undecided"),
            ("no title first is none", "\n---\nstatus: rejected\n---\n" + approved, None)]:
        failures += report("legacy_status", name, legacy_status(text), expected)
    with open(os.path.join(GATES_SCRIPTS, "..", "..", ".claude-plugin", "plugin.json"),
              encoding="utf-8") as handle:
        version = tuple(int(part) for part in json.load(handle)["version"].split("."))
    failures += report("legacy_status", "removed by its removed_in release",
                       version < LEGACY_STATUS_REMOVED_IN, True)
    with tempfile.TemporaryDirectory() as deep:
        failures += report("read_config", "project.json nested past the recursion limit",
                           result_or_message(lambda: read_config(write_scratch(
                               deep, "[" * 200000 + "]" * 200000, "project.json"))),
                           "project.json unreadable: project.json: not JSON: it nests too "
                           "deeply")
    with tempfile.TemporaryDirectory() as drafts:
        drafts_config = write_scratch(drafts, {}, ".claude/project.json")
        for name, text, expected in [
                ("a proposed draft's status", "---\nstatus: proposed\n---\n# D\n", "proposed"),
                ("a draft with no front matter is none", "# D\n\n## Decision\nPending.\n",
                 "none"),
                ("a status that is not text is refused", "---\nstatus: [a]\n---\n",
                 "has no text status"),
                ("unreadable front matter is refused", "---\nstatus: [a\n---\n",
                 "front matter is not YAML"),
                ("front matter with no status is refused", "---\ndate: 2026-10-26\n---\n",
                 "has no text status (None)"),
                ("a pre-front-matter approved record reads accepted",
                 "# D\n\n## Decision\n\nApproved by s on 2026-10-26.\n", "accepted"),
                ("a pre-front-matter rejected record reads rejected",
                 "# D\n\n## Decision\n\nRejected by s on 2026-10-26.\n", "rejected"),
                ("a pre-front-matter hand-edited Decision reads undecided",
                 "# D\n\n## Decision\n\nApproved.\n", "undecided"),
                ("a BOM before the title reads as pre-front-matter",
                 "\ufeff# D\n\n## Decision\n\nPending.\n", "none"),
                ("neither front matter nor a title is refused", "Notes\n", "no front matter")]:
            write_scratch(drafts, text, "d.md")
            got = result_or_message(lambda: front_matter_status("d.md", drafts_config))
            failures += report("front_matter_status", name, got == expected if
                               expected in ("proposed", "none", "accepted", "rejected",
                                            "undecided") else expected in got, True)
        write_scratch(drafts, "---\nstatus: proposed\n---\n# D\n", "cli.md")
        failures += cli_case(this, "front-matter-status prints a draft's status",
                             ["front-matter-status", "--file", "cli.md", "--config",
                              drafts_config], "proposed", 0, exact=True)
        write_scratch(drafts, "---\ndate: x\n---\n", "cli.md")
        failures += cli_case(this, "front-matter-status names a missing status",
                             ["front-matter-status", "--file", "cli.md", "--config",
                              drafts_config], "INVALID:", 1)
        write_scratch(drafts, "---\nstatus: proposed\n---\n", "s.md")
        hidden = subprocess.run([sys.executable, "-S", os.path.abspath(this),
                                 "front-matter-status", "--file", "s.md", "--config",
                                 drafts_config],
                                capture_output=True, text=True, check=False)
        failures += report("front_matter", "reads with the vendored PyYAML alone (python -S)",
                           (hidden.returncode, hidden.stdout.strip()), (0, "proposed"))
        with tempfile.TemporaryDirectory() as outside:
            write_scratch(outside, "---\nstatus: accepted\n---\n", "d.md")
            os.symlink(outside, os.path.join(drafts, "linked"))
            failures += report("front_matter_status", "a record under a symlinked folder is "
                               "refused", result_or_message(lambda: front_matter_status(
                                   "linked/d.md", drafts_config)).endswith(
                                   "is not a regular file reached through no symlink"), True)
        write_scratch(drafts, "---\nstatus: proposed\n---\n", "d.md")
        os.makedirs(os.path.join(drafts, "docs"), exist_ok=True)
        write_scratch(drafts, "---\nstatus: proposed\n---\n", "docs/d.md")
        failures += report("front_matter_status", "a template's doubled slash is read as one",
                           front_matter_status("docs//d.md", drafts_config), "proposed")
        for name, bad in [("a '..' path", "../d.md"), ("a leading '-'", "-d.md"),
                          ("a .git component", ".git/d.md")]:
            failures += report("front_matter_status", f"{name} is refused", result_or_message(
                lambda: front_matter_status(bad, drafts_config)).startswith("path "), True)
        write_scratch(drafts, b"---\nstatus: r\xf6\n---\n", "latin.md")
        failures += report("front_matter_status", "text that is not UTF-8 is named",
                           result_or_message(lambda: front_matter_status(
                               "latin.md", drafts_config)), "'latin.md' is not UTF-8 text")
        failures += report("front_matter_status", "a missing file is refused",
                           result_or_message(lambda: front_matter_status(
                               "gone.md", drafts_config)).endswith(
                               "is not a regular file reached through no symlink"), True)
    def nested(depth):
        return [] if depth == 1 else [nested(depth - 1)]

    for name, text, expected in [
            ("empty front matter is no mapping", "---\n---\n", "front matter is not a mapping"),
            ("a '...' closer alone ends it", "---\nstatus: accepted\n...\n",
             {"status": "accepted"}),
            ("two merge keys are repeated", "---\n<<: {status: proposed}\n<<: {status: accepted}\n"
             "---\n", "front matter is not YAML (a key is repeated)"),
            ("1 and 1.0 are distinct keys", "---\n1: a\n1.0: b\n---\n", {1: "a", 1.0: "b"}),
            ("a quoted and a plain key are one key", "---\nstatus: a\n\"status\": b\n---\n",
             "front matter is not YAML (a key is repeated)"),
            ("a closer never opened is none", "status: accepted\n---\n", "no front matter"),
            ("front matter nested past the recursion limit is refused",
             "---\nk: " + "[" * 5000 + "]" * 5000 + "\n---\n",
             "front matter is not YAML (nests too deeply)"),
            ("front matter at the depth cap is read",
             "---\nk: " + "[" * 127 + "]" * 127 + "\n---\n", {"k": nested(127)}),
            ("front matter just under the depth cap is read",
             "---\nk: " + "[" * 126 + "]" * 126 + "\n---\n", {"k": nested(126)}),
            ("front matter past the depth cap is refused",
             "---\nk: " + "[" * 128 + "]" * 128 + "\n---\n",
             "front matter is not YAML (nests too deeply)")]:
        got = result_or_message(lambda: front_matter(text))
        failures += report("front_matter", name, got == expected, True)
    with tempfile.TemporaryDirectory() as bare:
        # A ceiling at bare's parent keeps git from finding a repository the temporary
        # directory itself sits in.
        bare = os.path.realpath(bare)
        outside = isolated_git_environment(GIT_CEILING_DIRECTORIES=os.path.dirname(bare))
        with process_state(outside, bare):
            config_file = write_scratch(bare, {"design_dir": "docs/design"},
                                        ".claude/project.json")
            failures += report("design_read", "outside a repository the cause is kept",
                               "not a git repository" in result_or_message(lambda: design_read(
                                   "docs/design/ok.md", "main", config_file)), True)
    return failures


def design_transition_self_test(this):
    """design_transition over a scratch repository whose main holds an accepted, a proposed,
    and a rejected design, each working-tree status move tried on main, on its design
    branches, on another design's branch, and on a detached HEAD."""
    front = "---\nstatus: {}\ndate: 2026-10-30\ndecision-makers: rob\n---\n\n# D\n"
    failures = 0
    with tempfile.TemporaryDirectory() as root, \
            process_state(isolated_git_environment(), root):
        for status in ("accepted", "proposed", "rejected"):
            write_scratch(root, front.format(status), f"docs/design/{status}.md")
        project = write_scratch(root, {"design_dir": "docs/design"}, ".claude/project.json")
        run_git(root, "init", "--quiet", "--initial-branch=main")
        run_git(root, "add", "-A")
        run_git(root, "commit", "--quiet", "-m", "designs")
        on_main = "on 'main', not on design/"
        not_allowed = "which gates/design-exit.md does not allow"
        legacy = "# L\n\n## Decision\n\n{}\n"
        write_scratch(root, legacy.format("Approved by rob on 2026-10-30."),
                      "docs/design/legacy.md")
        run_git(root, "add", "-A")
        run_git(root, "commit", "--quiet", "-m", "a legacy design")
        for name, design, text, branch, expected in [
                ("an unchanged accepted design passes on main", "accepted", "accepted",
                 "main", "ok accepted -> accepted"),
                ("a new draft passes on main", "new", "proposed", "main",
                 "ok none -> proposed"),
                ("a legacy Pending draft passes on main", "new",
                 legacy.format("Pending — rob."), "main", "ok none -> none"),
                ("an unchanged legacy design passes on main", "legacy",
                 legacy.format("Approved by rob on 2026-10-30."), "main",
                 "ok accepted -> accepted"),
                ("a new design approved on main is refused", "new", "accepted", "main",
                 on_main),
                ("a new design rejected on main is refused", "new", "rejected", "main",
                 on_main),
                ("a new design decided on its branch passes", "new", "accepted", "design/new",
                 "ok none -> accepted"),
                ("an approval on its branch passes", "proposed", "accepted", "design/proposed",
                 "ok proposed -> accepted"),
                ("an approval on main is refused", "proposed", "accepted", "main", on_main),
                ("a rejection on a revision branch passes", "proposed", "rejected",
                 "design/proposed-rev2", "ok proposed -> rejected"),
                ("a reopen on main is refused", "accepted", "proposed", "main", on_main),
                ("a reopen on revision 1, the design's own branch, is refused", "accepted",
                 "proposed", "design/accepted-rev1", "on 'design/accepted-rev1'"),
                ("a reopen on revision 10 passes", "accepted", "proposed",
                 "design/accepted-rev10", "ok accepted -> proposed"),
                ("a reopen on its revision branch passes", "accepted", "proposed",
                 "design/accepted-rev2", "ok accepted -> proposed"),
                ("a reopen on another design's branch is refused", "accepted", "proposed",
                 "design/proposed-rev2", "on 'design/proposed-rev2', not on design/accepted"),
                ("a reopen on revision 0 is refused", "accepted", "proposed",
                 "design/accepted-rev0", "on 'design/accepted-rev0'"),
                ("a reopen on a zero-padded revision is refused", "accepted", "proposed",
                 "design/accepted-rev01", "on 'design/accepted-rev01'"),
                ("a reopen on a branch extending the slug is refused", "accepted", "proposed",
                 "design/accepted-x", "on 'design/accepted-x'"),
                ("accepted to rejected is refused on its branch", "accepted", "rejected",
                 "design/accepted", not_allowed),
                ("a rejected design reopened is refused", "rejected", "proposed",
                 "design/rejected-rev2", not_allowed),
                ("a status no transition names is refused", "proposed", "implemented",
                 "design/proposed", not_allowed),
                ("a reopen on a detached HEAD is refused", "accepted", "proposed", None,
                 "on a detached HEAD"),
                ("a deleted design is refused", "accepted", None, "design/accepted-rev2",
                 "'docs/design/accepted.md' is not a regular file")]:
            path = f"docs/design/{design}.md"
            if text is None:
                os.remove(os.path.join(root, path))
            else:
                write_scratch(root, text if text.startswith("#") else front.format(text), path)
            if branch is None:
                run_git(root, "checkout", "--quiet", "--detach", "main")
            else:
                run_git(root, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
            got = result_or_message(lambda: design_transition(path, "main", project))
            failures += report("design_transition", name, got == expected
                               if expected.startswith("ok ") else expected in got, True)
            run_git(root, "symbolic-ref", "HEAD", "refs/heads/main")
            run_git(root, "checkout", "--quiet", "--", ".")
            if design == "new":
                os.remove(os.path.join(root, path))
        path = "docs/design/accepted.md"
        run_git(root, "switch", "--quiet", "-c", "design/accepted-rev2")
        write_scratch(root, front.format("proposed"), path)
        run_git(root, "commit", "--quiet", "-am", "reopen")
        for name, status, expected in [
                ("a reopened design rejected against its reopen commit passes", "rejected",
                 "ok proposed -> rejected"),
                ("a reopened design approved against its reopen commit passes", "accepted",
                 "ok proposed -> accepted")]:
            write_scratch(root, front.format(status), path)
            failures += report("design_transition", name, result_or_message(
                lambda: design_transition(path, "HEAD", project)), expected)
        run_git(root, "checkout", "--quiet", "--", ".")
        run_git(root, "switch", "--quiet", "main")
        run_git(root, "branch", "--quiet", "-D", "design/accepted-rev2")
        write_scratch(root, front.format("proposed"), path)
        run_git(root, "commit", "--quiet", "-am", "a reopen by hand on main")
        write_scratch(root, front.format("accepted"), path)
        failures += report("design_transition", "a hand reopen approved on main is refused",
                           "on 'main', not on design/" in result_or_message(
                               lambda: design_transition(path, "HEAD", project)), True)
        run_git(root, "reset", "--quiet", "--hard", "HEAD~1")
        write_scratch(root, front.format("proposed"), "docs/design/accepted.md")
        failures += cli_case(this, "design-transition names the reopen made on main",
                             ["design-transition", "--ref", "main", "--config", project],
                             "INVALID: 'docs/design/accepted.md' moves accepted -> proposed "
                             "on 'main', not on design/accepted or design/accepted-rev<N>", 1,
                             input="docs/design/accepted.md\n", cwd=root,
                             env=isolated_git_environment(), exact=True)
        run_git(root, "symbolic-ref", "HEAD", "refs/heads/design/accepted-rev2")
        failures += cli_case(this, "design-transition passes the reopen on its branch",
                             ["design-transition", "--ref", "main", "--config", project],
                             "ok accepted -> proposed", 0, input="docs/design/accepted.md\n",
                             cwd=root, env=isolated_git_environment(), exact=True)
        write_scratch(root, {}, ".claude/project.json")
        failures += report("design_transition", "an unset design_dir is named",
                           result_or_message(lambda: design_transition(
                               "docs/design/accepted.md", "main", project)),
                           "design_dir is unset in project.json")
    return failures


def lifecycle_self_test(this):
    """lifecycle over a scratch repository whose `base` branch stands for the parent's
    origin ref: one fixture per LIFECYCLE_STATES state, and the merged, squash-merged, and
    stale-marker cases each state's neighbor could swallow."""
    front = "---\nstatus: {}\n---\n\n# D\n\n## Summary\n\n{}\n"
    failures = 0
    with tempfile.TemporaryDirectory() as root, \
            process_state(isolated_git_environment(), root):
        project = write_scratch(root, {"design_dir": "docs/design"}, ".claude/project.json")
        write_scratch(root, front.format("accepted", "Epic: AB-1"), "docs/design/a.md")
        write_scratch(root, front.format("rejected", "x"), "docs/design/x.md")
        write_scratch(root, front.format("proposed", "x"), "docs/design/h.md")
        run_git(root, "init", "--quiet", "--initial-branch=main")
        run_git(root, "add", "-A")
        run_git(root, "commit", "--quiet", "-m", "designs")
        run_git(root, "branch", "design/a")
        run_git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
        blob = blob_at(root, "origin/main", "docs/design/a.md")

        def check(name, text, expected, epic=False):
            got = result_or_message(lambda: lifecycle(text, "origin/main", project, epic))
            return report("lifecycle", name, got, expected)

        draft = "# [E1] D\nJira: {}\n\n- Design: `docs/design/a.md`\n\n# [S1] T\n" \
                "Handoff: a-01\nJira: {}\n{}"
        reviewed = ("<!-- review round 2 -->\n## S1 — NOT PLANNABLE\n### BLOCKER\n- f\n"
                    "### MAJOR\n- g\n")
        failures += check("no design names an Epic", "AB-9",
                          ["no-design no design names AB-9",
                           "NEXT: /delivery-kit:design-feature AB-9"], epic=True)
        failures += check("a path with no design", "docs/design/n.md",
                          ["no-design docs/design/n.md does not exist",
                           "NEXT: /delivery-kit:design-feature docs/design/n.md"])
        write_scratch(root, front.format("proposed", "w"), "docs/design/w.md")
        failures += check("a draft in the working tree", "docs/design/w.md",
                          ["design-draft docs/design/w.md in the working tree",
                           "NEXT: /delivery-kit:design-feature docs/design/w.md"])
        os.remove(os.path.join(root, "docs/design/w.md"))
        failures += check("an accepted design with no draft", "docs/design/a.md",
                          ["design-accepted-on-parent docs/design/a.md",
                           "NEXT: /delivery-kit:write-tickets docs/design/a.md"])
        failures += check("an Epic key finds its design", "AB-1",
                          ["design-accepted-on-parent docs/design/a.md",
                           "NEXT: /delivery-kit:write-tickets docs/design/a.md"], epic=True)
        failures += check("a rejected design", "docs/design/x.md",
                          ["design-rejected docs/design/x.md on origin/main",
                           "NEXT: none — a rejected design is the record of a stop; a new "
                           "request starts a new design"])
        failures += check("a design reopened by hand on the parent", "docs/design/h.md",
                          ["design-draft docs/design/h.md is proposed on origin/main, "
                           "reopened there by hand", "NEXT: /delivery-kit:design-feature docs/design/h.md"])
        write_scratch(root, draft.format("", "", ""), "docs/tickets/a.md")
        failures += check("an unreviewed ticket draft", "docs/design/a.md",
                          ["tickets-draft docs/tickets/a.md: not yet reviewed",
                           "NEXT: /delivery-kit:write-tickets docs/design/a.md"])
        write_scratch(root, draft.format("", "", reviewed), "docs/tickets/a.md")
        failures += check("a reviewed ticket draft", "docs/design/a.md",
                          ["tickets-draft docs/tickets/a.md: review round 2, 1 BLOCKER",
                           "NEXT: /delivery-kit:write-tickets docs/design/a.md"])
        rework = "<!-- design-rework: S1 @ {} -->\n"
        write_scratch(root, draft.format("", "", reviewed + rework.format(blob)),
                      "docs/tickets/a.md")
        failures += check("a draft stalled on design rework", "docs/design/a.md",
                          ["tickets-stalled-needs-design-rework docs/tickets/a.md: S1",
                           "NEXT: /delivery-kit:design-feature AB-1"])
        write_scratch(root, draft.format("", "", reviewed + rework.format("0" * 40)),
                      "docs/tickets/a.md")
        failures += check("a rework line for an older design is stale", "docs/design/a.md",
                          ["tickets-draft docs/tickets/a.md: review round 2, 1 BLOCKER",
                           "NEXT: /delivery-kit:write-tickets docs/design/a.md"])
        write_scratch(root, draft.format("AB-1", "AB-2", reviewed + "<!-- tickets created -->\n"),
                      "docs/tickets/a.md")
        failures += check("every ticket created", "docs/design/a.md",
                          ["tickets-created a-01", "NEXT: /delivery-kit:plan-work a-01"])
        os.remove(os.path.join(root, "docs/tickets/a.md"))
        run_git(root, "switch", "--quiet", "-c", "design/a-rev2")
        write_scratch(root, front.format("proposed", "Epic: AB-1"), "docs/design/a.md")
        run_git(root, "commit", "--quiet", "-am", "reopen")
        run_git(root, "switch", "--quiet", "main")
        failures += check("a reopen in progress on its revision branch", "docs/design/a.md",
                          ["design-draft docs/design/a.md on design/a-rev2",
                           "NEXT: /delivery-kit:design-feature AB-1"])
        run_git(root, "switch", "--quiet", "design/a-rev2")
        write_scratch(root, front.format("accepted", "Epic: AB-1\nRevised."), "docs/design/a.md")
        run_git(root, "commit", "--quiet", "-am", "decide")
        run_git(root, "switch", "--quiet", "main")
        failures += check("a decided revision awaiting its pull request", "docs/design/a.md",
                          ["design-in-review docs/design/a.md on design/a-rev2",
                           "NEXT: git push -u origin design/a-rev2, then merge its pull request"])
        run_git(root, "checkout", "--quiet", "design/a-rev2", "--", "docs/design/a.md")
        run_git(root, "commit", "--quiet", "-m", "squash-merge the revision")
        run_git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
        failures += check("a squash-merged revision and a merged branch are no review",
                          "docs/design/a.md", ["design-accepted-on-parent docs/design/a.md",
                                               "NEXT: /delivery-kit:write-tickets "
                                               "docs/design/a.md"])
        write_scratch(root, front.format("proposed", "Epic: AB-1"), "docs/design/a.md")
        run_git(root, "commit", "--quiet", "-am", "a reopen on main")
        failures += check("a reopen committed on the parent, unpushed", "docs/design/a.md",
                          ["design-unpushed main is ahead of origin/main on docs/design/a.md",
                           "NEXT: git switch -c design/a-rev3 && git branch -f main origin/main"])
        run_git(root, "switch", "--quiet", "-c", "feature/x")
        failures += check("design commits on a branch that is not the parent never reset it",
                          "docs/design/a.md", ["design-accepted-on-parent docs/design/a.md",
                                               "NEXT: /delivery-kit:write-tickets "
                                               "docs/design/a.md"])
        run_git(root, "switch", "--quiet", "main")
        run_git(root, "branch", "--quiet", "-D", "feature/x")
        run_git(root, "reset", "--quiet", "--hard", "origin/main")
        state = run_git(root, "rev-parse", "--path-format=absolute", "--git-path",
                        "design-feature").strip()
        write_scratch(root, "a\n", os.path.join(state, "slug"))
        failures += check("an interrupted Step 6", "docs/design/a.md",
                          [f"design-step6-interrupted {state}",
                           "NEXT: /delivery-kit:design-feature AB-1 (continue or abort)"])
        failures += cli_case(this, "lifecycle prints its state and NEXT line",
                             ["lifecycle", "--ref", "origin/main", "--config", project],
                             "design-rejected docs/design/x.md on origin/main", 0, line=0,
                             input="docs/design/x.md\n", cwd=root, env=isolated_git_environment(),
                             exact=True)
        failures += cli_case(this, "lifecycle refuses a path outside design_dir",
                             ["lifecycle", "--ref", "origin/main", "--config", project],
                             "INVALID: path 'src/x.md' is not directly under design_dir", 1,
                             input="src/x.md\n", cwd=root, env=isolated_git_environment())
    return failures


def lifecycle_edges_self_test(this):
    """lifecycle's lookups and refusals: an Epic found in the working tree or on a design
    branch, unsafe and spaced file names, a branch sharing a slug's prefix, a remote design
    branch, a new design committed on the parent, a status no step writes, bad input, and
    tickets_state's boundaries."""
    front = "---\nstatus: {}\n---\n\n# D\n\n## Summary\n\n{}\n"
    failures = 0
    with tempfile.TemporaryDirectory() as root, \
            process_state(isolated_git_environment(), root):
        project = write_scratch(root, {"design_dir": "docs/design"}, ".claude/project.json")
        write_scratch(root, front.format("accepted", "Epic: AB-5"), "docs/design/a;touch.md")
        write_scratch(root, front.format("accepted", "x"), "docs/design/my notes.md")
        write_scratch(root, front.format("implemented", "x"), "docs/design/odd.md")
        write_scratch(root, front.format("accepted", "x"), "docs/design/c.md")
        run_git(root, "init", "--quiet", "--initial-branch=main")
        run_git(root, "add", "-A")
        run_git(root, "commit", "--quiet", "-m", "designs")
        run_git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
        blob = blob_at(root, "origin/main", "docs/design/c.md")

        def check(name, text, expected, epic=False, ref="origin/main"):
            got = result_or_message(lambda: lifecycle(text, ref, project, epic))
            return report("lifecycle", name, got if isinstance(expected, list) else
                          isinstance(got, str) and got.startswith(expected), expected
                          if isinstance(expected, list) else True)

        failures += check("a file name no slug allows is never a design", "AB-5",
                          ["no-design no design names AB-5",
                           "NEXT: /delivery-kit:design-feature AB-5"], epic=True)
        write_scratch(root, front.format("proposed", "Epic: AB-6"), "docs/design/w.md")
        failures += check("an Epic found in the working tree", "AB-6",
                          ["design-draft docs/design/w.md in the working tree",
                           "NEXT: /delivery-kit:design-feature AB-6"], epic=True)
        os.remove(os.path.join(root, "docs/design/w.md"))
        run_git(root, "switch", "--quiet", "-c", "design/b")
        write_scratch(root, front.format("accepted", "Epic: AB-7"), "docs/design/b.md")
        run_git(root, "add", "-A")
        run_git(root, "commit", "--quiet", "-m", "b")
        run_git(root, "switch", "--quiet", "main")
        failures += check("an Epic found on a design branch", "AB-7",
                          ["design-in-review docs/design/b.md on design/b",
                           "NEXT: git push -u origin design/b, then merge its pull request"],
                          epic=True)
        run_git(root, "update-ref", "refs/remotes/origin/design/b", "design/b")
        run_git(root, "branch", "--quiet", "-D", "design/b")
        failures += check("a design branch only on origin is in review", "docs/design/b.md",
                          ["design-in-review docs/design/b.md on origin/design/b",
                           "NEXT: git push -u origin design/b, then merge its pull request"])
        run_git(root, "update-ref", "-d", "refs/remotes/origin/design/b")
        run_git(root, "switch", "--quiet", "-c", "design/c-revamp")
        write_scratch(root, front.format("proposed", "y"), "docs/design/c.md")
        run_git(root, "commit", "--quiet", "-am", "another design's branch")
        run_git(root, "switch", "--quiet", "main")
        failures += check("a branch sharing the slug's prefix is not its revision",
                          "docs/design/c.md", ["design-accepted-on-parent docs/design/c.md",
                                               "NEXT: /delivery-kit:write-tickets "
                                               "docs/design/c.md"])
        write_scratch(root, front.format("proposed", "n"), "docs/design/n.md")
        run_git(root, "add", "-A")
        run_git(root, "commit", "--quiet", "-m", "a new design on main")
        failures += check("a new design committed on the parent, unpushed", "docs/design/n.md",
                          ["design-unpushed main is ahead of origin/main on docs/design/n.md",
                           "NEXT: git switch -c design/n && git branch -f main origin/main"])
        run_git(root, "reset", "--quiet", "--hard", "origin/main")
        failures += check("a status no step writes is invalid", "docs/design/odd.md",
                          "'docs/design/odd.md' in origin/main has status 'implemented'")
        failures += check("a key that is no Jira key is invalid", "nope", "'nope' is not a",
                          epic=True)
        failures += check("a ref naming no commit is invalid", "docs/design/c.md",
                          "ref '--all' does not name a commit", ref="--all")
        draft = ("# [E1] D\nJira: {}\n\n- Design: `docs/design/c.md`\n\n# [S1] T\n"
                 "{}Jira: {}\n{}")
        round_text = "<!-- review round 1 -->\n## S1\n### BLOCKER\n{}### MAJOR\n- m\n"
        for name, content, expected in [
                ("no BLOCKER", draft.format("", "", "", round_text.format("")),
                 "tickets-draft docs/tickets/c.md: review round 1, 0 BLOCKERs"),
                ("two BLOCKERs", draft.format("", "", "", round_text.format("- a\n- b\n")),
                 "tickets-draft docs/tickets/c.md: review round 1, 2 BLOCKERs"),
                ("some tickets created", draft.format("AB-1", "", "", ""),
                 "tickets-draft docs/tickets/c.md: not yet reviewed"),
                ("every ticket fetched for rewrite is no creation",
                 draft.format("AB-1", "Baseline: AB-2\n", "AB-2", ""),
                 "tickets-draft docs/tickets/c.md: not yet reviewed"),
                ("every ticket created, no handoff",
                 draft.format("AB-1", "", "AB-2", "<!-- tickets created -->\n"),
                 "tickets-created"),
                ("a fetched Epic after Step 8 is created",
                 draft.format("AB-1", "Baseline: AB-2\n", "AB-2", "<!-- tickets created -->\n"),
                 "tickets-created"),
                ("a quoted created line is no marker",
                 draft.format("AB-1", "", "AB-2", "> <!-- tickets created -->\n"),
                 "tickets-draft docs/tickets/c.md: not yet reviewed"),
                ("the matching rework line names its tickets",
                 draft.format("", "", "", f"<!-- design-rework: S1 @ {blob} -->\n"
                              f"<!-- design-rework: S9 @ {'0' * 40} -->\n"),
                 "tickets-stalled-needs-design-rework docs/tickets/c.md: S1")]:
            write_scratch(root, content, "docs/tickets/c.md")
            failures += report("tickets_state", name, result_or_message(
                lambda: lifecycle("docs/design/c.md", "origin/main", project))[0], expected)
        os.symlink("c.md", os.path.join(root, "docs/tickets/l.md"))
        os.remove(os.path.join(root, "docs/tickets/c.md"))
        failures += report("tickets_state", "a symlinked draft is skipped", lifecycle(
            "docs/design/c.md", "origin/main", project)[0],
            "design-accepted-on-parent docs/design/c.md")
        write_scratch(root, b"---\nstatus: accepted\n---\n# L r\xf6b\nEpic: AB-8\n",
                      "docs/design/latin.md")
        write_scratch(root, front.format("accepted", "Epic: AB-8"), "docs/design/later.md")
        run_git(root, "add", "-A")
        run_git(root, "commit", "--quiet", "-m", "a design that is not UTF-8")
        run_git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
        failures += check("a parent design that is not UTF-8 is invalid", "docs/design/latin.md",
                          "'docs/design/latin.md' in origin/main is not UTF-8 text")
        failures += check("an Epic scan skips a design that is not UTF-8", "AB-8",
                          ["design-accepted-on-parent docs/design/later.md",
                           "NEXT: /delivery-kit:write-tickets docs/design/later.md"], epic=True)
        failures += cli_case(this, "design-read names design-feature for a missing design",
                             ["design-read", "--ref", "origin/main", "--config", project],
                             "NEXT: /delivery-kit:design-feature docs/design/gone.md", 1,
                             line=1, stderr_prefixes=("NEXT",), input="docs/design/gone.md\n",
                             cwd=root, env=isolated_git_environment(), exact=True)
        write_scratch(root, {}, ".claude/project.json")
        failures += check("an unset design_dir is named", "docs/design/c.md",
                          "design_dir is unset in project.json")
    return failures


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
    path_cases = [
        ("a design under its directory", "docs/design/x.md", "docs/design", "design_dir", True),
        ("a second line", "docs/design/x.md\ndocs/design/y.md", "docs/design", "design_dir", ""),
        ("a '..' component", "docs/design/../x.md", "docs/design", "design_dir", ""),
        ("a '.' component", "docs/design/./x.md", "docs/design", "design_dir", ""),
        ("an empty component", "docs/design//x.md", "docs/design", "design_dir", ""),
        ("a path outside the directory", "docs/designs/x.md", "docs/design", "design_dir", ""),
        ("a path that is not .md", "docs/design/x.txt", "docs/design", "design_dir", ""),
        ("a bare .md", "docs/design/.md", "docs/design", "design_dir", ""),
        ("a ref prefix", "HEAD:docs/design/x.md", "docs/design", "design_dir", ""),
        ("a nested path", "docs/design/sub/x.md", "docs/design", "design_dir", ""),
        ("a nested bare .md", "docs/design/sub/.md", "docs/design", "design_dir", ""),
        ("a name that is no slug", "docs/design/-x.md", "docs/design", "design_dir", ""),
        ("an uppercase name", "docs/design/X.md", "docs/design", "design_dir", ""),
        ("an ADR under its directory", "docs/adr/0001-use-location.md", "docs/adr", "adr_dir",
         True),
        ("a trailing slash on the directory", "docs/design/x.md", "docs/design/", "design_dir",
         True),
        ("a trailing slash joined by a template", "docs/design//x.md", "docs/design/",
         "design_dir", True),
        ("a second empty component after a trailing slash", "docs/design///x.md",
         "docs/design/", "design_dir", ""),
        ("two trailing slashes joined by a template", "docs/design///x.md", "docs/design//",
         "design_dir", True),
        ("an invalid directory", "../d/x.md", "../d", "design_dir", "design_dir"),
        ("an invalid ADR directory names adr_dir", "../adr/0001-x.md", "../adr", "adr_dir",
         "adr_dir"),
        ("an ADR path outside its directory names adr_dir", "docs/design/x.md", "docs/adr",
         "adr_dir", "path 'docs/design/x.md' is not directly under adr_dir"),
        ("an empty directory component names design_dir", "docs/design/x.md", "docs//design",
         "design_dir", "design_dir"),
    ]
    for name, path, directory, key, expected in path_cases:
        error = error_message(lambda: design_path(path, directory, key))
        failures += report("design_path", name, error is None if expected is True else
                           error is not None and error.startswith(expected), True)
    failures += design_read_self_test(this)
    failures += design_transition_self_test(this)
    failures += lifecycle_self_test(this)
    failures += lifecycle_edges_self_test(this)
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
    reading = commands.add_parser("design-read")
    reading.add_argument("--ref", required=True)
    reading.add_argument("--config", required=True)
    reading.add_argument("--key", choices=("design_dir", "adr_dir"), default="design_dir")
    output = reading.add_mutually_exclusive_group()
    output.add_argument("--path", action="store_true")
    output.add_argument("--status", action="store_true")
    status = commands.add_parser("front-matter-status")
    status.add_argument("--file", required=True)
    status.add_argument("--config", required=True)
    transition = commands.add_parser("design-transition")
    transition.add_argument("--ref", required=True)
    transition.add_argument("--config", required=True)
    stage = commands.add_parser("lifecycle")
    stage.add_argument("--ref", required=True)
    stage.add_argument("--config", required=True)
    stage.add_argument("--epic", action="store_true")
    brief = commands.add_parser("brief-read")
    brief.add_argument("--config", required=True)
    brief.add_argument("--path", action="store_true")
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
                              "design-read": lambda: design_read(text_input(None), args.ref,
                                                                 args.config, args.key,
                                                                 args.path, args.status),
                              "design-transition": lambda: design_transition(
                                  text_input(None), args.ref, args.config),
                              "lifecycle": lambda: lifecycle(text_input(None), args.ref,
                                                             args.config, args.epic),
                              "brief-read": lambda: brief_read(args.config, args.path),
                              "front-matter-status": lambda: front_matter_status(args.file,
                                                                                 args.config)},
                     args.command)


if __name__ == "__main__":
    sys.exit(main())
