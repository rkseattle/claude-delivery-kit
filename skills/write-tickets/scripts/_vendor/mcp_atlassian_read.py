"""Vendored from mcp-atlassian 0.21.0 (MIT, see LICENSE.mcp-atlassian): the stdlib part
of the read jira_get_issue applies to a description. Verbatim: _extract_blocks and
_restore_blocks (preprocessing/base.py); _convert_panel and JiraPreprocessor's
_process_mentions, _process_smart_links, jira_to_markdown, _convert_jira_list_to_markdown
(preprocessing/jira.py). Not vendored: clean_jira_text's last step,
_convert_html_to_markdown, which needs BeautifulSoup and markdownify; html_step_triggered
below is its trigger test, verbatim. Do not edit; re-vendor instead (README.md).
"""
from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("mcp-atlassian")


def _extract_blocks(
    text: str,
    pattern: str,
    transform_fn: Callable[[re.Match[str]], str],
    storage: list[str],
    prefix: str,
    flags: int = 0,
) -> str:
    """Extract blocks matching pattern, transform, store, and replace with placeholders.

    Args:
        text: Input text to process.
        pattern: Regex pattern to match blocks.
        transform_fn: Function to transform the match into the target format.
        storage: List to store transformed blocks.
        prefix: Placeholder prefix (e.g., "CODEBLOCK").
        flags: Regex flags to pass to ``re.sub``.

    Returns:
        Text with blocks replaced by placeholders.
    """

    def _replacer(match: re.Match[str]) -> str:
        transformed = transform_fn(match)
        placeholder = f"\x00{prefix}{len(storage)}\x00"
        storage.append(transformed)
        return placeholder

    return re.sub(pattern, _replacer, text, flags=flags)


def _restore_blocks(text: str, storage: list[str], prefix: str) -> str:
    """Restore blocks from placeholders.

    Replaces in reverse order (highest index first) to avoid
    index collisions when placeholder text contains digits.

    Args:
        text: Text with placeholders.
        storage: List of stored blocks.
        prefix: Placeholder prefix used during extraction.

    Returns:
        Text with placeholders replaced by stored blocks.
    """
    for i in range(len(storage) - 1, -1, -1):
        text = text.replace(f"\x00{prefix}{i}\x00", storage[i])
    return text


def _convert_panel(params: str | None, content: str) -> str:
    """Convert a Jira {panel} block to markdown."""
    title = ""
    if params:
        title_match = re.search(r"title=([^|}]+)", params)
        if title_match:
            title = title_match.group(1).strip()
    content = content.strip()
    if title:
        return f"\n**{title}**\n{content}\n"
    return f"\n{content}\n"


class JiraReader:
    """JiraPreprocessor's text methods, as the connector runs them with translation on."""

    def __init__(self, base_url: str = "") -> None:
        self.base_url = base_url
        self.disable_translation = False

    def _process_mentions(self, text: str, pattern: str) -> str:
        """
        Process user mentions in text.

        Args:
            text: The text containing mentions
            pattern: Regular expression pattern to match mentions

        Returns:
            Text with mentions replaced with display names
        """
        mentions = re.findall(pattern, text)
        for account_id in mentions:
            try:
                # Note: This is a placeholder - actual user fetching should be injected
                display_name = f"User:{account_id}"
                text = text.replace(f"[~accountid:{account_id}]", display_name)
            except Exception as e:
                logger.error(f"Error processing mention for {account_id}: {str(e)}")
        return text

    def _process_smart_links(self, text: str) -> str:
        """Process Jira/Confluence smart links."""
        # Pattern matches: [text|url|smart-link]
        link_pattern = r"\[(.*?)\|(.*?)\|smart-link\]"
        matches = re.finditer(link_pattern, text)

        for match in matches:
            full_match = match.group(0)
            link_text = match.group(1)
            link_url = match.group(2)

            # Extract issue key if it's a Jira issue link
            issue_key_match = re.search(r"browse/([A-Z][A-Z0-9_]+-\d+)", link_url)
            # Check if it's a Confluence wiki link
            confluence_match = re.search(
                r"wiki/spaces/.+?/pages/\d+/(.+?)(?:\?|$)", link_url
            )

            if issue_key_match:
                issue_key = issue_key_match.group(1)
                clean_url = f"{self.base_url}/browse/{issue_key}"
                text = text.replace(full_match, f"[{issue_key}]({clean_url})")
            elif confluence_match:
                url_title = confluence_match.group(1)
                readable_title = url_title.replace("+", " ")
                readable_title = re.sub(r"^[A-Z][A-Z0-9_]+-\d+\s+", "", readable_title)
                text = text.replace(full_match, f"[{readable_title}]({link_url})")
            else:
                clean_url = link_url.split("?")[0]
                text = text.replace(full_match, f"[{link_text}]({clean_url})")

        return text

    def jira_to_markdown(self, input_text: str) -> str:
        """
        Convert Jira markup to Markdown format.

        Args:
            input_text: Text in Jira markup format

        Returns:
            Text in Markdown format (or original text if translation disabled)
        """
        if not input_text:
            return ""

        if self.disable_translation:
            return input_text

        output = input_text

        # Protect code/noformat/inline-code blocks from downstream
        # transformations by replacing them with placeholders.
        #
        # Trade-off: when {quote} wraps a {code} block, the code
        # content is extracted *before* the {quote} handler runs.
        # The {quote} handler prefixes each remaining line with
        # "> " but cannot reach inside the already-extracted block.
        # After restoration the opening fence line may carry "> "
        # while inner code lines do not, breaking blockquote
        # continuity.  This is intentional: protecting code content
        # from markup corruption is more important than preserving
        # blockquote indentation around code fences.
        code_blocks: list[str] = []
        inline_codes: list[str] = []

        def _jira_code_to_md(match: re.Match[str]) -> str:
            lang = match.group(1) or ""
            content = match.group(2)
            return f"```{lang}\n{content}\n```"

        output = _extract_blocks(
            output,
            r"\{code(?::([a-z]+))?\}([\s\S]*?)\{code\}",
            _jira_code_to_md,
            code_blocks,
            "CODEBLOCK",
            flags=re.MULTILINE,
        )
        output = _extract_blocks(
            output,
            r"\{noformat\}([\s\S]*?)\{noformat\}",
            lambda m: f"```\n{m.group(1)}\n```",
            code_blocks,
            "CODEBLOCK",
        )
        output = _extract_blocks(
            output,
            r"\{\{([^}]+)\}\}",
            lambda m: f"`{m.group(1)}`",
            inline_codes,
            "INLINECODE",
        )

        # Block quotes
        output = re.sub(r"^bq\.(.*?)$", r"> \1\n", output, flags=re.MULTILINE)

        # Text formatting (bold, italic)
        output = re.sub(
            r"([*_])(.*?)\1",
            lambda match: ("**" if match.group(1) == "*" else "*")
            + match.group(2)
            + ("**" if match.group(1) == "*" else "*"),
            output,
        )

        # Multi-level numbered list
        output = re.sub(
            r"^((?:#|-|\+|\*)+) (.*)$",
            lambda match: self._convert_jira_list_to_markdown(match),
            output,
            flags=re.MULTILINE,
        )

        # Headers
        output = re.sub(
            r"^h([0-6])\.(.*)$",
            lambda match: "#" * int(match.group(1)) + match.group(2),
            output,
            flags=re.MULTILINE,
        )

        # Citation (non-overlapping alternation to avoid catastrophic backtracking)
        output = re.sub(
            r"\?\?([^?]+(?:\?[^?]+)*)\?\?",
            r"<cite>\1</cite>",
            output,
        )

        # Inserted text
        output = re.sub(r"\+([^+]*)\+", r"<ins>\1</ins>", output)

        # Superscript
        output = re.sub(r"\^([^^]*)\^", r"<sup>\1</sup>", output)

        # Subscript
        output = re.sub(r"~([^~]*)~", r"<sub>\1</sub>", output)

        # Strikethrough
        output = re.sub(r"-([^-]*)-", r"-\1-", output)

        # Quote blocks
        output = re.sub(
            r"\{quote\}([\s\S]*)\{quote\}",
            lambda match: "\n".join(
                [f"> {line}" for line in match.group(1).split("\n")]
            ),
            output,
            flags=re.MULTILINE,
        )

        # Panel blocks - extract content, optionally show title as bold
        output = re.sub(
            r"\{panel(?::([^}]*))?\}([\s\S]*?)\{panel\}",
            lambda match: _convert_panel(match.group(1), match.group(2)),
            output,
            flags=re.MULTILINE,
        )

        # Images with alt text
        output = re.sub(
            r"!([^|\n\s]+)\|([^\n!]*)alt=([^\n!\,]+?)"
            r"(,([^\n!]*))?!",
            r"![\3](\1)",
            output,
        )

        # Images with other parameters (ignore them)
        output = re.sub(r"!([^|\n\s]+)\|([^\n!]*)!", r"![](\1)", output)

        # Images without parameters
        output = re.sub(r"!([^\n\s!]+)!", r"![](\1)", output)

        # Links
        output = re.sub(r"\[([^|]+)\|(.+?)\]", r"[\1](\2)", output)
        output = re.sub(r"\[(.+?)\]([^\(])", r"\1\2", output)

        # Colored text
        output = re.sub(
            r"\{color:([^}]+)\}([\s\S]*?)\{color\}",
            r"<span style=\"color:\1\">\2</span>",
            output,
            flags=re.MULTILINE,
        )

        # Convert Jira table headers (||) to markdown table format
        lines = output.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            if "||" in line:
                # Replace Jira table headers
                lines[i] = lines[i].replace("||", "|")

                # Add a separator line for markdown tables
                header_cells = lines[i].count("|") - 1
                if header_cells > 0:
                    separator_line = "|" + "---|" * header_cells
                    lines.insert(i + 1, separator_line)
                    i += 1

            i += 1

        # Rejoin the lines
        output = "\n".join(lines)

        # Restore code/noformat blocks and inline code
        output = _restore_blocks(output, code_blocks, "CODEBLOCK")
        output = _restore_blocks(output, inline_codes, "INLINECODE")

        return output

    def _convert_jira_list_to_markdown(self, match: re.Match) -> str:
        """
        Helper method to convert Jira lists to Markdown format.

        Args:
            match: Regex match object containing the Jira list markup

        Returns:
            Markdown-formatted list item
        """
        jira_bullets = match.group(1)
        content = match.group(2)

        # Calculate indentation level based on number of symbols
        indent_level = len(jira_bullets) - 1
        indent = " " * (indent_level * 2)

        # Determine the marker based on the last character
        last_char = jira_bullets[-1]
        prefix = "1." if last_char == "#" else "-"

        return f"{indent}{prefix} {content}"


def html_step_triggered(text: str) -> bool:
    """Whether clean_jira_text's _convert_html_to_markdown would re-render this text:
    its protection of code blocks and spans, then its trigger test, verbatim."""
    code_blocks: list[str] = []
    inline_codes: list[str] = []
    text = _extract_blocks(
        text,
        r"```[^\n]*\n[\s\S]*?\n```",
        lambda m: m.group(0),
        code_blocks,
        "HTMLCVTBLOCK",
    )
    text = _extract_blocks(
        text,
        r"`[^`]+`",
        lambda m: m.group(0),
        inline_codes,
        "HTMLCVTINLINE",
    )
    return bool(re.search(r"<[^>]+>", text))
