#!/usr/bin/env bash
# Every path reference/rule-book-map.md names is a tracked file, so a row cannot go on citing
# a kit file that moved or was deleted. A path is a code span whose text contains a slash,
# read from the repo root; other spans and text outside backticks are prose. The map is
# parsed by the CommonMark parser project_rules vendors, with GFM tables on since the map's
# rows are tables, so a span is exactly what a renderer shows as code. A path is matched
# against `git ls-files` exactly, not tested on disk, so an untracked file, a wrongly cased
# name on a case-insensitive disk, or a path climbing out of the repo fails here as in CI. A
# missing map, or one naming no path, fails too, rather than reading as no broken references.
# Usage: rule-book-map.sh [repo-root]
set -euo pipefail
root="${1:-.}"
gates="$(cd "$(dirname "$0")/../../gates/scripts" && pwd)"
python3 - "$root" "$gates" <<'PY'
import os
import subprocess
import sys

root, gates = sys.argv[1:3]
sys.dont_write_bytecode = True
sys.path.insert(0, gates)
from project_rules import MARKDOWN_VENDOR, vendored  # noqa: E402

vendored(MARKDOWN_VENDOR)
from markdown_it import MarkdownIt  # noqa: E402

path = os.path.join(root, "reference", "rule-book-map.md")
try:
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
except OSError as error:
    sys.exit(f"no rule-book map at {path}: {error.strerror}")
except UnicodeDecodeError as error:
    sys.exit(f"{path} is not UTF-8: byte {error.start}")


def code_spans(tokens):
    """The text of every code span, in document order, table cells included."""
    for token in tokens:
        if token.type == "code_inline":
            yield token.content
        yield from code_spans(token.children or ())


paths = sorted({span for span in code_spans(MarkdownIt("commonmark").enable("table").parse(text))
                if "/" in span})
if not paths:
    sys.exit(f"{path} names no path")
listing = subprocess.run(["git", "-C", root, "ls-files", "-z"], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
if listing.returncode != 0:
    sys.exit(f"cannot list the tracked files under {root}")
tracked = set(os.fsdecode(name) for name in listing.stdout.split(b"\0") if name)
failed = False
for span in paths:
    if span in tracked:
        print(f"ok: {span}")
    else:
        print(f"MISSING: {span}")
        failed = True
sys.exit(1 if failed else 0)
PY
