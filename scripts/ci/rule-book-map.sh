#!/usr/bin/env bash
# Every path reference/rule-book-map.md names is tracked, so a row cannot go on citing
# a kit file that moved or was deleted. A path is a code span whose text contains a slash,
# read from the repo root; other spans and text outside backticks are prose. The map is
# parsed by the CommonMark parser project_rules vendors, with GFM tables on since the map's
# rows are tables, so a span is exactly what a renderer shows as code. A path must be a file
# or directory git tracks, by project_rules' one rule, so an untracked file, a wrongly cased
# name on a case-insensitive disk, or a path climbing out of the repo fails here as in CI. A
# missing map, or one naming no path, fails too, rather than reading as no broken references.
#
# Every map table has an Excepted by column, the one place a row cites an exception: each
# name there, separated by semicolons, must start the Rule cell of a complete row under
# gates/exceptions.md's Kit-wide exceptions heading, followed by a colon, complete as
# project_rules' complete_register_row defines it for every register reader. Expiry is not
# checked: deliver lists expired rows at each run, and a check that turned red on a date
# would fail a branch for a change it never made. Removing or renaming that row then fails
# here rather than leaving the map claiming an exception that is gone. Both documents'
# tables are read from the parsed Markdown, not by a line pattern.
# Usage: rule-book-map.sh [repo-root]
set -euo pipefail
root="${1:-.}"
gates="$(cd "$(dirname "$0")/../../gates/scripts" && pwd)"
python3 - "$root" "$gates" <<'PY'
import os
import sys

root, gates = sys.argv[1:3]
sys.dont_write_bytecode = True
sys.path.insert(0, gates)
from project_rules import (REGISTER_COLUMNS, complete_register_row, is_register_header,  # noqa: E402
                           markdown_tables, markdown_tokens, tracked_path_matcher,
                           words)

EXCEPTED_BY = "Excepted by"


def read(path, missing):
    """The file's text, or exit naming why it cannot be read."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as error:
        sys.exit(f"{missing} at {path}: {error.strerror}")
    except UnicodeDecodeError as error:
        sys.exit(f"{path} is not UTF-8: byte {error.start}")


path = os.path.join(root, "reference", "rule-book-map.md")
text = read(path, "no rule-book map")
tokens = markdown_tokens(text)


def code_spans(tokens):
    """The text of every code span, in document order, table cells included."""
    for token in tokens:
        if token.type == "code_inline":
            yield token.content
        yield from code_spans(token.children or ())


paths = sorted({span for span in code_spans(tokens) if "/" in span})
if not paths:
    sys.exit(f"{path} names no path")
try:
    is_tracked = tracked_path_matcher(root)
except ValueError as error:
    sys.exit(str(error))
failed = False
for span in paths:
    if is_tracked(span):
        print(f"ok: {span}")
    else:
        print(f"MISSING: {span}")
        failed = True
cited = set()
for header, rows in markdown_tables(tokens):
    if EXCEPTED_BY not in header:
        print(f"NO {EXCEPTED_BY.upper()} COLUMN: the map table headed {' | '.join(header)}")
        failed = True
        continue
    column = header.index(EXCEPTED_BY)
    for row in rows:
        cited |= {words(name) for name in row[column].split(";") if name.strip()}
if cited:
    exceptions = os.path.join(root, "gates", "exceptions.md")
    rules = []
    for header, rows in markdown_tables(markdown_tokens(read(exceptions, "no exceptions register")),
                                        "Kit-wide exceptions"):
        if not is_register_header(header):
            print(f"NOT A REGISTER: a Kit-wide exceptions table in {exceptions} is headed "
                  f"{' | '.join(header)}, not {' | '.join(REGISTER_COLUMNS)}")
            failed = True
            continue
        rules += [words(row[0]) for row in rows if complete_register_row(row)]
    for name in sorted(cited):
        if any(rule.startswith(name + ":") for rule in rules):
            print(f"ok: excepted by {name}")
        else:
            print(f"MISSING ROW: {name} starts no complete row's Rule cell under Kit-wide "
                  f"exceptions in {exceptions}")
            failed = True
sys.exit(1 if failed else 0)
PY
