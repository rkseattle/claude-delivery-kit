#!/usr/bin/env python3
"""Static checks for a README.md.

Usage: python3 check_readme.py [path/to/README.md]   exit 0 clean, 1 on any error
       python3 check_readme.py --self-test          runs tests/fixtures; exit 0 only if all match
Relative links resolve against the README's directory.
"""
import argparse
import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

MAX_BYTES = 500 * 1024  # GitHub truncates rendered READMEs beyond 500 KiB
WARN_LINES = 400
REQUIRED = {  # one heading must contain one keyword from each group
    "install": ["install", "getting started", "setup", "quickstart", "quick start"],
    "usage": ["usage", "example", "quickstart", "quick start", "getting started"],
    "license": ["license", "licence"],
}
# The template's own placeholders (references/readme-template.md); the self-test checks the
# list against it. project-name is the template's title, so it counts only outside code.
CODE_PLACEHOLDER = re.compile(
    r"\b(INSTALL-COMMAND|EXAMPLE-COMMAND|REAL-OUTPUT|TEST-COMMAND-FROM-CI|SPDX-ID|"
    r"RUNTIME-NAME|VERSION-RANGE|OTHER-DEPS|EXAMPLE_VAR)\b"
)
PLACEHOLDER = re.compile(CODE_PLACEHOLDER.pattern + r"|(?<![\w-])project-name(?![\w-])")
# CommonMark 0.31.2: fences (4.5), setext headings (4.3), code spans (6.1), link
# destinations (6.3) with one level of balanced parentheses, and reference definitions
# (4.7); a `[^label]:` line is a GitHub footnote, not a link.
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
SETEXT_UNDERLINE = re.compile(r"^ {0,3}(=+|-+)\s*$")
LIST_OR_QUOTE = re.compile(r"^\s*([-*+>]|\d+[.)])(\s|$)")
CODE_SPAN = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)")
LINK_DESTINATION = re.compile(r"\]\(\s*(<[^>]*>|(?:[^()\s]|\([^()\s]*\))+)")
REFERENCE_DEF = re.compile(r"^ {0,3}\[(?!\^)[^\]]+\]:\s*(<[^>]*>|\S+)")
# Not after a URL's host or another path segment: https://host/Users/x is a link, not a path.
ABS_PATH = re.compile(r"(?<![\w.:/-])(/Users/\w+|/home/\w+/|C:\\Users\\)")
# Block quote and list markers ahead of a heading on the same line (CommonMark 5.1, 5.2).
CONTAINER_PREFIX = re.compile(r"^ {0,3}(?:>\s?|(?:[-*+]|\d+[.)])\s+)+")
SKILL_DIR = Path(__file__).resolve().parent.parent
FIXTURES = SKILL_DIR / "tests" / "fixtures"
SKILL_FILES = ["SKILL.md", "references/readme-template.md", "references/checklist.md",
               "scripts/check_readme.py"]


def split_fences(lines):
    """Return (prose, code) as lists of (line_number, text), and warnings for bare fences.

    Code is fenced blocks — indented further inside a list item — and indented blocks:
    four or more spaces (a tab counts as four) after a blank line or a heading, outside a
    list (CommonMark 4.4, 4.5, 5.2), where indentation continues a list item instead.
    """
    prose, code, warnings = [], [], []
    fence = None  # (char, length, indent) of the open fence
    can_start_indented, indented, in_list = True, False, False
    for number, line in enumerate(lines, 1):
        line = line.expandtabs(4)
        indent = len(line) - len(line.lstrip(" "))
        if fence is None:
            match = FENCE_OPEN.match(line[indent - min(indent, 3):] if in_list else line)
            if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
                fence = (match.group(1)[0], len(match.group(1)), indent)
                if not match.group(2).strip():
                    warnings.append(("fence-language", f"line {number}: code fence without language tag"))
                can_start_indented, indented = False, False
                continue
            blank = not line.strip()
            if not blank and indent >= 4 and (can_start_indented or indented) and not in_list:
                code.append((number, line))
                indented = True
                continue
            if not blank and indent == 0:
                in_list = bool(LIST_OR_QUOTE.match(line))
            indented = indented and blank
            can_start_indented = blank or bool(re.match(r"^ {0,3}#{1,6}(\s|$)", line))
            prose.append((number, line))
            continue
        closing = line.strip()
        if (indent <= fence[2] + 3 and closing
                and set(closing) == {fence[0]} and len(closing) >= fence[1]):
            fence, can_start_indented = None, False
            continue
        code.append((number, line))
    return prose, code, warnings


def repo_root(directory):
    """The nearest ancestor holding .git, which GitHub resolves a leading-slash link from."""
    for candidate in (directory, *directory.parents):
        if (candidate / ".git").exists():
            return candidate
    return directory


def link_target_exists(base, root, target):
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", target, re.I):
        return True
    path = unquote(target.split("#")[0].split("?")[0])
    if not path:
        return True
    candidate = (root / path.lstrip("/") if path.startswith("/") else base / path).resolve()
    try:
        candidate.relative_to(root.resolve())  # GitHub cannot serve a path above the repo
    except ValueError:
        return False
    return exists_exactly(candidate)


def exists_exactly(path):
    """Exists with this exact case in every component, as GitHub's case-sensitive paths need;
    macOS and Windows file systems would otherwise accept `license` for `LICENSE`."""
    path = Path(path)
    if not path.exists():
        return False
    resolved = Path(path.anchor)
    for part in path.parts[1:]:
        if part in (".", ""):
            continue
        if part == "..":
            resolved = resolved.parent
            continue
        if part not in {entry.name for entry in resolved.iterdir()}:
            return False
        resolved = resolved / part
    return True


def outside_comments(prose):
    """Drop prose inside HTML comments, which GitHub does not render. Comment markers
    inside inline code are text, so code spans are masked while looking for them."""
    kept, in_comment = [], False
    for number, line in prose:
        masked = CODE_SPAN.sub(lambda span: " " * len(span.group()), line)
        position, pieces = 0, []
        if in_comment:
            end = masked.find("-->")
            if end < 0:
                continue
            position, in_comment = end + 3, False
        while True:
            start = masked.find("<!--", position)
            if start < 0:
                pieces.append(line[position:])
                break
            pieces.append(line[position:start])
            end = masked.find("-->", start + 4)
            if end < 0:
                in_comment = True
                break
            position = end + 3
        kept.append((number, "".join(pieces)))
    return kept


def find_headings(prose):
    """ATX (#) and setext (underlined) headings as (line_number, level, title)."""
    headings, previous = [], None
    for number, line in prose:
        # A closing run of # counts only after a space, so "## C#" keeps its "#" (4.2).
        atx = re.match(r"^ {0,3}(#{1,6})(?:\s+(.*?))?(?:\s+#+)?\s*$", CONTAINER_PREFIX.sub("", line))
        underline = SETEXT_UNDERLINE.match(line)
        if atx:
            headings.append((number, len(atx.group(1)), (atx.group(2) or "").strip()))
            previous = None
            continue
        if (underline and previous and previous[0] == number - 1 and previous[1].strip()
                and not LIST_OR_QUOTE.match(previous[1])):
            level = 1 if underline.group(1)[0] == "=" else 2
            headings.append((previous[0], level, previous[1].strip()))
            previous = None
            continue
        previous = (number, line)
    return headings


def check(path, root=None):
    """Return (errors, warnings), each a list of (code, message)."""
    raw = path.read_bytes()
    lines = raw.decode(errors="replace").splitlines()
    base = path.resolve().parent
    root = root or repo_root(base)
    errors, warnings = [], []

    if len(raw) > MAX_BYTES:
        errors.append(("size", f"size {len(raw):,} bytes exceeds 500 KiB"))
    if len(lines) > WARN_LINES:
        warnings.append(("length", f"{len(lines)} lines; consider moving sections to docs/"))

    prose, code, fence_warnings = split_fences(lines)
    warnings.extend(fence_warnings)
    for number, line in code:
        if CODE_PLACEHOLDER.search(line):
            errors.append(("placeholder", f"line {number}: template placeholder: {line.strip()[:80]}"))
        if ABS_PATH.search(line):
            warnings.append(("absolute-path", f"line {number}: absolute local path in code block"))

    prose = outside_comments(prose)
    headings = find_headings(prose)

    h1_count = sum(1 for heading in headings if heading[1] == 1)
    h1_count += sum(len(re.findall(r"<h1[\s>]", CODE_SPAN.sub("", line), re.I)) for _, line in prose)
    if h1_count != 1:
        errors.append(("h1-count", f"expected exactly one H1, found {h1_count}"))
    previous = 0
    for number, level, title in headings:
        if previous and level > previous + 1:
            warnings.append(("heading-skip", f"line {number}: heading jumps H{previous} -> H{level} ('{title}')"))
        previous = level

    titles = [title.lower() for _, _, title in headings]
    for name, keys in REQUIRED.items():
        if not any(key in title for title in titles for key in keys):
            errors.append(("missing-section", f"no '{name}' section (looked for: {', '.join(keys)})"))

    for number, line in prose:
        outside_code = CODE_SPAN.sub("", line)
        targets = [m.group(1) for m in LINK_DESTINATION.finditer(outside_code)]
        reference = REFERENCE_DEF.match(outside_code)
        if reference:
            targets.append(reference.group(1))
        for target in targets:
            if not link_target_exists(base, root, target):
                errors.append(("broken-link", f"line {number}: broken relative link '{target}'"))
        if re.search(r"!\[\s*\]\(", outside_code):
            warnings.append(("image-alt", f"line {number}: image without alt text"))
        if PLACEHOLDER.search(line):
            errors.append(("placeholder", f"line {number}: template placeholder: {line.strip()[:80]}"))
        if ABS_PATH.search(line):
            warnings.append(("absolute-path", f"line {number}: absolute local path"))
    return errors, warnings


def report(errors, warnings):
    for code, message in warnings:
        print(f"WARN:  {code}: {message}")
    for code, message in errors:
        print(f"ERROR: {code}: {message}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")


def self_test():
    """Each fixture's first line declares the error and warning codes it must produce."""
    failures = 0

    def result(ok, name, detail=""):
        nonlocal failures
        print(f"{'ok  ' if ok else 'FAIL'} {name}{'' if ok else ': ' + detail}")
        failures += not ok

    expect = re.compile(r"<!-- expect errors=([a-z0-9,-]*) warnings=([a-z0-9,-]*) -->")
    fixtures = sorted(FIXTURES.glob("*.md"))
    result(bool(fixtures), "fixtures present", f"none under {FIXTURES}")
    # A leading-slash link resolves from two levels above this skill, the same tree it sits
    # in under skills/, .claude/skills/, or ~/.claude/skills/.
    root = SKILL_DIR.parent.parent
    for fixture in fixtures:
        declared = expect.match((fixture.read_text(encoding="utf-8").splitlines() or [""])[0])
        if not declared:
            result(False, fixture.name, "first line has no <!-- expect ... --> header")
            continue
        errors, warnings = check(fixture, root)
        want = (sorted(filter(None, declared.group(1).split(","))),
                sorted(filter(None, declared.group(2).split(","))))
        got = (sorted(code for code, _ in errors), sorted(code for code, _ in warnings))
        result(got == want, fixture.name, f"expected {want}, got {got}")

    titles = [title for _, _, title in find_headings([(1, "## C#"), (2, "## Done ##")])]
    result(titles == ["C#", "Done"], "closing # needs a space before it", str(titles))

    for fixture, code in (("three-errors.md", 1), ("clean.md", 0)):
        run = subprocess.run([sys.executable, __file__, str(FIXTURES / fixture)],
                             stdout=subprocess.DEVNULL)
        result(run.returncode == code, f"exit {code} on {fixture}", f"got {run.returncode}")

    body = "# widget\n\n## Install\n\n## Usage\n\n## License\n"
    with tempfile.TemporaryDirectory() as scratch:
        long_file = Path(scratch) / "long.md"
        long_file.write_text(body + "text\n" * WARN_LINES, encoding="utf-8")
        _, warnings = check(long_file)
        result([c for c, _ in warnings] == ["length"], "length warning past the line limit", str(warnings))
        big_file = Path(scratch) / "big.md"
        big_file.write_text(body + ("x" * 99 + "\n") * (MAX_BYTES // 100 + 1), encoding="utf-8")
        errors, _ = check(big_file)
        result([c for c, _ in errors] == ["size"], "size error past 500 KiB", str(errors))

    template = (SKILL_DIR / "references" / "readme-template.md").read_text(encoding="utf-8")
    skeleton = template.split("````markdown", 1)[-1].split("````", 1)[0]
    tokens = set(re.findall(r"\b[A-Z]{2,}(?:[-_][A-Z]{2,})+\b", skeleton)) | {"project-name"}
    missed = sorted(token for token in tokens if not PLACEHOLDER.search(token))
    result(not missed, "every template placeholder is flagged", str(missed))

    for name in SKILL_FILES:
        result((SKILL_DIR / name).is_file(), f"skill file {name}", "missing")
    front = re.match(r"---\n(.*?)\n---\n", (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"), re.S)
    fields = dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", front.group(1), re.M)) if front else {}
    result(bool(fields.get("description", "").strip()), "frontmatter description", "empty")

    source = Path(__file__).read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, feature_version=(3, 8))
        result(True, "parses with the Python 3.8 grammar")
    except SyntaxError as error:
        result(False, "parses with the Python 3.8 grammar", str(error))
        tree = ast.parse(source)
    imported = {alias.name.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) and node.module}
    stdlib = getattr(sys, "stdlib_module_names", None)
    if stdlib is None:
        print("skip stdlib-only imports: needs Python 3.10+ to enumerate the standard library")
    else:
        result(imported <= stdlib, "stdlib-only imports", str(sorted(imported - stdlib)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description="Static checks for a README.md.")
    parser.add_argument("path", nargs="?", default="README.md")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    path = Path(args.path)
    if not path.is_file():
        print(f"ERROR: missing: {path} not found")
        return 1
    errors, warnings = check(path)
    report(errors, warnings)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
