#!/usr/bin/env python3
"""Static checks for a README.md.

Usage: python3 check_readme.py [path/to/README.md]   exit 0 clean, 1 on any error
       python3 check_readme.py --self-test          runs tests/fixtures; exit 0 only if all match
Relative links resolve against the README's directory, and leading-slash links against the
repository root.

Markdown is parsed by markdown-it-py, a CommonMark parser vendored under _vendor/, so block
structure (quotes, lists, fences, HTML blocks) is the parser's, not a reconstruction of it.
"""
import argparse
import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

VENDOR = Path(__file__).resolve().parent / "_vendor"
sys.path.insert(0, str(VENDOR))
from markdown_it import MarkdownIt  # noqa: E402  vendored, see _vendor/README.md

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
# Not after a URL's host or another path segment: https://host/Users/x is a link, not a path.
ABS_PATH = re.compile(r"(?<![\w.:/-])(/Users/\w+|/home/\w+/|C:\\Users\\)")
# HTML that GitHub renders: a and img targets, img alt text, and h1 titles.
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
HTML_TARGET = re.compile(r"<(?:a|img)\b[^>]*?\b(?:href|src)\s*=\s*[\"']([^\"']+)[\"']", re.I)
HTML_IMG = re.compile(r"<img\b[^>]*>", re.I)
HTML_ALT = re.compile(r"\balt\s*=\s*[\"'][^\"']+", re.I)
HTML_H1 = re.compile(r"<h1[\s>]", re.I)
SKILL_DIR = Path(__file__).resolve().parent.parent
FIXTURES = SKILL_DIR / "tests" / "fixtures"
SKILL_FILES = ["SKILL.md", "references/readme-template.md", "references/checklist.md",
               "scripts/check_readme.py"]


def set_aside_footnote_definitions(state):
    """A `[^label]:` line is a GitHub footnote, not a link reference definition. It is moved
    out of the reference table before inline parsing, so `[^label]` stays text, and its
    source lines are kept so the footnote's own text can be checked."""
    references = state.env.get("references", {})
    for label in [label for label in references if label.startswith("^")]:
        state.env.setdefault("footnotes", []).append(references.pop(label).get("map"))


def parser():
    # CommonMark plus GitHub's tables and strikethrough; raw HTML stays on, as GitHub renders it.
    markdown = MarkdownIt("commonmark").enable(["table", "strikethrough"])
    markdown.core.ruler.after("block", "footnotes", set_aside_footnote_definitions)
    return markdown


def repo_root(directory):
    """The nearest ancestor holding .git, which GitHub resolves a leading-slash link from."""
    for candidate in (directory, *directory.parents):
        if (candidate / ".git").exists():
            return candidate
    return directory


def exists_exactly(path, root):
    """Exists with this exact case in every component below root, as GitHub's case-sensitive
    paths need; macOS and Windows file systems would otherwise accept `license` for
    `LICENSE`. path is resolved and inside root."""
    if not path.exists():
        return False
    current = root
    for part in path.relative_to(root).parts:
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError:
            return True  # unreadable directory: existence is all that can be checked
        if part not in names:
            return False
        current = current / part
    return True


def link_target_exists(base, root, target):
    if re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", target, re.I):
        return True
    path = unquote(target.split("#")[0].split("?")[0])
    if not path:
        return True
    candidate = (root / path.lstrip("/") if path.startswith("/") else base / path).resolve()
    root = root.resolve()
    try:
        candidate.relative_to(root)  # GitHub cannot serve a path above the repo
    except ValueError:
        return False
    return exists_exactly(candidate, root)


class Findings:
    """Errors and warnings as (code, message). A broken target is reported once; any other
    finding once per distinct message."""

    def __init__(self):
        self.errors, self.warnings, self.seen = [], [], set()

    def add(self, severity, code, line, message, key=None):
        key = (code, key if key is not None else (line, message))
        if key in self.seen:
            return
        self.seen.add(key)
        findings = self.errors if severity == "error" else self.warnings
        findings.append((code, f"line {line}: {message}" if line else message))


def scan_text(findings, text, line, in_code):
    """Placeholders and absolute paths in one run of rendered text or code."""
    pattern = CODE_PLACEHOLDER if in_code else PLACEHOLDER
    if pattern.search(text):
        findings.add("error", "placeholder", line, f"template placeholder: {' '.join(text.split())[:80]}")
    if ABS_PATH.search(text):
        findings.add("warning", "absolute-path", line,
                     "absolute local path in code block" if in_code else "absolute local path")


def scan_html(findings, html, line, check_target):
    """Rendered HTML, comments removed (an unclosed one hides the rest, as GitHub renders
    it): its text, a and img targets, img alt, line by line; returns the h1 count."""
    html = HTML_COMMENT.sub(lambda comment: "\n" * comment.group().count("\n"), html)
    html = html.split("<!--", 1)[0]
    in_pre = False
    for offset, html_line in enumerate(html.split("\n")):
        opens = len(re.findall(r"<(?:pre|code)\b", html_line, re.I))
        closes = len(re.findall(r"</(?:pre|code)>", html_line, re.I))
        scan_text(findings, re.sub(r"<[^>]*>", " ", html_line), line + offset,
                  in_code=in_pre or opens > 0)
        in_pre = (in_pre or opens > closes) and not (closes > opens)
        for match in HTML_TARGET.finditer(html_line):
            check_target(match.group(1), line + offset)
        for tag in HTML_IMG.findall(html_line):
            if not HTML_ALT.search(tag):
                findings.add("warning", "image-alt", line + offset, "image without alt text")
    return len(HTML_H1.findall(html))


def scan_inline(findings, children, line, check_target):
    """One paragraph's inline tokens, counting lines from the parser's break tokens and the
    newlines inside raw HTML. Returns (h1 count, line after the last child)."""
    h1_count = 0
    for child in children or []:
        if child.type in ("softbreak", "hardbreak"):
            line += 1
        elif child.type == "text":
            scan_text(findings, child.content, line, in_code=False)
        elif child.type == "code_inline":
            scan_text(findings, child.content, line, in_code=True)
        elif child.type == "html_inline":
            h1_count += scan_html(findings, child.content, line, check_target)
            line += child.content.count("\n")
        elif child.type == "link_open":
            check_target(child.attrGet("href") or "", line)
        elif child.type == "image":
            check_target(child.attrGet("src") or "", line)
            if not child.content.strip():
                findings.add("warning", "image-alt", line, "image without alt text")
            image_h1, line = scan_inline(findings, child.children, line, check_target)
            h1_count += image_h1
    return h1_count, line


def scan_tokens(findings, tokens, check_target, line_offset=0):
    """Every block of a parsed document; returns (headings, h1 count from HTML)."""
    headings, h1_count, line = [], 0, line_offset + 1
    for position, token in enumerate(tokens):
        if token.map:
            line = line_offset + token.map[0] + 1
        if token.type == "heading_open":
            headings.append((line, int(token.tag[1]), tokens[position + 1].content.strip()))
        elif token.type in ("fence", "code_block"):
            first = line + (1 if token.type == "fence" else 0)
            if token.type == "fence" and not token.info.strip():
                findings.add("warning", "fence-language", line, "code fence without language tag")
            for offset, code_line in enumerate(token.content.splitlines()):
                scan_text(findings, code_line, first + offset, in_code=True)
        elif token.type == "html_block":
            h1_count += scan_html(findings, token.content, line, check_target)
        elif token.type == "inline":
            h1_count += scan_inline(findings, token.children, line, check_target)[0]
    return headings, h1_count


def check(path, root=None):
    """Return (errors, warnings), each a list of (code, message)."""
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")  # GitHub ignores a byte order mark
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")  # as CommonMark splits
    if lines and lines[-1] == "":
        lines.pop()
    base = path.resolve().parent
    root = root or repo_root(base)
    findings = Findings()

    def check_target(target, line):
        if not link_target_exists(base, root, target):
            findings.add("error", "broken-link", line, f"broken relative link '{unquote(target)}'",
                         key=unquote(target))

    if len(raw) > MAX_BYTES:
        findings.add("error", "size", None, f"size {len(raw):,} bytes exceeds 500 KiB")
    if len(lines) > WARN_LINES:
        findings.add("warning", "length", None, f"{len(lines)} lines; consider moving sections to docs/")

    env = {}
    headings, h1_count = scan_tokens(findings, parser().parse(text, env), check_target)
    for reference in env.get("references", {}).values():
        check_target(reference["href"], reference["map"][0] + 1 if reference.get("map") else None)
    for mapped in env.get("footnotes", []):
        if mapped:  # a footnote's text is Markdown of its own: parse it after its label
            body = re.sub(r"^\s*\[\^[^\]]*\]:", "", "\n".join(lines[mapped[0]:mapped[1]]), count=1)
            scan_tokens(findings, parser().parse(body, {}), check_target, line_offset=mapped[0])

    h1_count += sum(1 for heading in headings if heading[1] == 1)
    if h1_count != 1:
        findings.add("error", "h1-count", None, f"expected exactly one H1, found {h1_count}")
    previous_level = 0
    for line, level, title in headings:
        if previous_level and level > previous_level + 1:
            findings.add("warning", "heading-skip", line, f"heading jumps H{previous_level} -> H{level} ('{title}')")
        previous_level = level

    titles = [title.lower() for _, _, title in headings]
    for name, keys in REQUIRED.items():
        if not any(key in title for title in titles for key in keys):
            findings.add("error", "missing-section", None, f"no '{name}' section (looked for: {', '.join(keys)})",
                         key=name)
    return findings.errors, findings.warnings


def report(errors, warnings):
    for code, message in warnings:
        print(f"WARN:  {code}: {message}")
    for code, message in errors:
        print(f"ERROR: {code}: {message}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")


def as_declared(findings, declared_codes):
    """Codes in a fixture header's form: code@line where the header pins that code's line."""
    pinned = {code.split("@")[0] for code in declared_codes if "@" in code}
    shown = []
    for code, message in findings:
        line = re.match(r"line (\d+)", message)
        shown.append(f"{code}@{line.group(1)}" if code in pinned and line else code)
    return sorted(shown)


def imports_of(tree):
    """Top-level module names an AST imports absolutely."""
    names = {alias.name.split(".")[0] for node in ast.walk(tree)
             if isinstance(node, ast.Import) for alias in node.names}
    names |= {node.module.split(".")[0] for node in ast.walk(tree)
              if isinstance(node, ast.ImportFrom) and node.module and not node.level}
    return names


def self_test():
    """Each fixture's first line declares the error and warning codes it must produce."""
    failures = 0

    def result(ok, name, detail=""):
        nonlocal failures
        print(f"{'ok  ' if ok else 'FAIL'} {name}{'' if ok else ': ' + detail}")
        failures += not ok

    # A code may carry @line to pin where it is reported: errors=broken-link@16,h1-count
    expect = re.compile(r"<!-- expect errors=([a-z0-9,@-]*) warnings=([a-z0-9,@-]*) -->")
    fixtures = sorted(FIXTURES.glob("*.md"))
    result(bool(fixtures), "fixtures present", f"none under {FIXTURES}")
    # A leading-slash link resolves from two levels above this skill, the same tree it sits
    # in under skills/, .claude/skills/, or ~/.claude/skills/.
    root = SKILL_DIR.parent.parent
    for fixture in fixtures:
        declared = expect.match((fixture.read_text(encoding="utf-8-sig").splitlines() or [""])[0])
        if not declared:
            result(False, fixture.name, "first line has no <!-- expect ... --> header")
            continue
        errors, warnings = check(fixture, root)
        want = (sorted(filter(None, declared.group(1).split(","))),
                sorted(filter(None, declared.group(2).split(","))))
        got = (as_declared(errors, want[0]), as_declared(warnings, want[1]))
        result(got == want, fixture.name, f"expected {want}, got {got}")

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

    # The checker and everything it vendors must parse as Python 3.8 and import only the
    # standard library, the vendored packages, or linkify_it, which markdown-it imports
    # inside a try block and the checker never enables.
    vendored = {entry.name for entry in VENDOR.iterdir() if entry.is_dir()}
    sources = [Path(__file__)] + sorted(VENDOR.rglob("*.py"))
    syntax_errors, imported = [], set()
    for source in sources:
        text = source.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, feature_version=(3, 8))
        except SyntaxError as error:
            syntax_errors.append(f"{source.name}: {error}")
            tree = ast.parse(text)
        imported |= imports_of(tree)
    result(not syntax_errors, "parses with the Python 3.8 grammar", "; ".join(syntax_errors))
    stdlib = getattr(sys, "stdlib_module_names", None)
    if stdlib is None:
        print("skip stdlib-only imports: needs Python 3.10+ to enumerate the standard library")
    else:
        foreign = sorted(imported - stdlib - vendored - {"linkify_it"})
        result(not foreign, "imports only the standard library and _vendor/", str(foreign))
    return 1 if failures else 0


def main():
    argument_parser = argparse.ArgumentParser(description="Static checks for a README.md.")
    argument_parser.add_argument("path", nargs="?", default="README.md")
    argument_parser.add_argument("--self-test", action="store_true")
    args = argument_parser.parse_args()
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
