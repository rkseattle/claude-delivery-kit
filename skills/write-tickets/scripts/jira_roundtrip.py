"""What `jira_get_issue` returns for a description write-tickets Step 8 sent to Jira Cloud.

    write   the Atlassian MCP connector's markdown_to_adf, vendored verbatim
    store   Jira renders the ADF document as wiki markup for the read: adf_to_wiki below,
            written from Jira's text-formatting notation
    read    the connector's clean_jira_text: its standard-library steps vendored verbatim;
            its HTML step, when its own trigger fires, as BeautifulSoup's html.parser and
            markdownify 1.2.2's defaults treat text: tags dropped with their text kept,
            entities decoded, whitespace collapsed per text node, * and _ escaped

The pieces not vendored are pinned by three live probes of Jira Cloud, each written with the
connector and read back with jira_get_issue: for every line sent, the model must agree with
Jira on whether it came back unchanged, the one thing the linter asks of it.
"""
import html
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
from mcp_atlassian_adf import markdown_to_adf  # noqa: E402  vendored, see _vendor/README.md
from mcp_atlassian_read import (  # noqa: E402
    JiraReader, _extract_blocks, _restore_blocks, html_step_triggered)

WIKI_MARKS = {"code": ("{{", "}}"), "strong": ("*", "*"), "em": ("_", "_"), "strike": ("-", "-")}


# Jira escapes the ! of an image-like !x! in plain text, and nothing else in plain text.
WIKI_IMAGE = re.compile(r"!([^\s!][^!\n]*)!")


def inline_wiki(nodes):
    out = []
    for node in nodes:
        text = node.get("text", "")
        if not any(mark["type"] == "code" for mark in node.get("marks", [])):
            text = WIKI_IMAGE.sub(r"\\!\1\\!", text)
        for mark in node.get("marks", []):
            if mark["type"] == "link":
                text = f"[{text}|{mark['attrs']['href']}]"
            elif mark["type"] in WIKI_MARKS:
                opening, closing = WIKI_MARKS[mark["type"]]
                text = f"{opening}{text}{closing}"
        out.append(text)
    return "".join(out)


def block_wiki(node):
    kind = node["type"]
    if kind == "paragraph":
        return inline_wiki(node.get("content", []))
    if kind == "heading":
        return f"h{node['attrs']['level']}. {inline_wiki(node.get('content', []))}"
    if kind in ("bulletList", "orderedList"):
        marker = "*" if kind == "bulletList" else "#"
        return "\n".join(f"{marker} {inline_wiki(item['content'][0].get('content', []))}"
                         for item in node["content"])
    if kind == "codeBlock":
        lang = node.get("attrs", {}).get("language")
        macro = f"{{code:{lang}}}" if lang else "{noformat}"
        return f"{macro}{node['content'][0]['text']}{'{code}' if lang else '{noformat}'}"
    if kind == "blockquote":
        return "{quote}" + "\n".join(block_wiki(p) for p in node["content"]) + "{quote}"
    if kind == "rule":
        return "----"
    if kind == "table":
        rows = []
        for row in node["content"]:
            sep = "||" if row["content"][0]["type"] == "tableHeader" else "|"
            cells = [inline_wiki(c["content"][0].get("content", [])) for c in row["content"]]
            rows.append(sep + sep.join(cells) + sep)
        return "\n".join(rows)
    raise ValueError(f"no wiki rendering for ADF node {kind}")


def adf_to_wiki(doc):
    return "\n\n".join(block_wiki(node) for node in doc["content"])


HTML_TAG = re.compile(r"(<[A-Za-z/!][^>]*>)")


def markdownify_text(node):
    """markdownify's process_text on one html.parser text node, wrap off."""
    node = html.unescape(node)
    node = re.sub(r"[\t \r\n]*[\r\n][\t \r\n]*", "\n", node)
    node = re.sub(r"[\t ]+", " ", node)
    return node.replace("*", r"\*").replace("_", r"\_")


def markdownify_plain(text):
    """The connector's _convert_html_to_markdown on text its trigger fired for: code kept
    verbatim, each tag dropped, each text node between tags converted."""
    blocks, spans = [], []
    text = _extract_blocks(text, r"```[^\n]*\n[\s\S]*?\n```", lambda m: m.group(0), blocks, "MDBLOCK")
    text = _extract_blocks(text, r"`[^`]+`", lambda m: m.group(0), spans, "MDSPAN")
    parts = HTML_TAG.split(text)
    text = "".join(markdownify_text(p) for n, p in enumerate(parts) if n % 2 == 0).strip("\n")
    return _restore_blocks(_restore_blocks(text, spans, "MDSPAN"), blocks, "MDBLOCK")


def read(wiki):
    """clean_jira_text, as jira_get_issue applies it to a description."""
    reader = JiraReader()
    text = reader._process_mentions(wiki, r"\[~accountid:(.*?)\]")
    text = reader._process_smart_links(text)
    text = reader.jira_to_markdown(text)
    if html_step_triggered(text):
        text = markdownify_plain(text)
    return text.strip()


def roundtrip(markdown):
    """The description jira_get_issue returns after Step 8 writes this Markdown."""
    return read(adf_to_wiki(markdown_to_adf(markdown)))


# (sent, read): written to a live Jira Cloud issue with the connector, read back with
# jira_get_issue, and the issue restored. Covers every construct the model renders.
PROBES = [
    ("""Goal: Users stay signed in for 30 days.

## Probe

- P1: bare tag [verify: inspection @ skills/write-tickets/SKILL.md]
- P2: code-span tag `[verify: inspection @ skills/write-tickets/SKILL.md]`
- P3: backslash-escaped tag \\[verify: inspection @ skills/write-tickets/SKILL.md\\]
- P4: children `[children: S1, S2]` and bare [children: S1, S2]
- P5: p95 response < 300 ms at 200 requests/second, availability >= 99.9%, Login->dashboard
- P6: path src/auth/__init__.py and `src/auth/__init__.py`
- P7: **Bold** and _underscore_ and snake_case_name and a*b*c
- P8: link [docs](https://example.com) and value list `[200, 404]` and quoted `[R14]`
- [ ] P9 task item
- P10: ampersand & less-than < and pipe | and hash # inline

A hard-wrapped paragraph whose first line ends here
and whose second line continues it.

1. Numbered one
2. Numbered two""", """Goal: Users stay signed in for 30 days.
## Probe
- P1: bare tag verify: inspection @ skills/write-tickets/SKILL.md
- P2: code-span tag `[verify: inspection @ skills/write-tickets/SKILL.md]`
- P3: backslash-escaped tag \\verify: inspection @ skills/write-tickets/SKILL.md\\
- P4: children `[children: S1, S2]` and bare children: S1, S2
- P5: p95 response < 300 ms at 200 requests/second, availability >= 99.9%, Login->dashboard
- P6: path src/auth/\\*\\*init\\*\\*.py and `src/auth/__init__.py`
- P7: \\*\\*Bold\\* and \\*underscore\\* and snake\\*case\\*name and a\\*b\\*c
- P8: link [docs](https://example.com) and value list `[200, 404]` and quoted `[R14]`
- P9 task item
- P10: ampersand & less-than < and pipe | and hash # inline
A hard-wrapped paragraph whose first line ends here
and whose second line continues it.
1. Numbered one
1. Numbered two"""),
    ("""Goal: Probe two.

## Probe two

- Q1: lone plus C+ and caret x^2 and tilde ~30 and cite ?? here
- Q2: pairs x^2 y^3 and ~30 to ~45 and a ?? b ?? c and d + e + f
- Q3: image !warning! and !logo.png|width=40! and braces {{name}} and table a||b
- Q4: strike ~~gone~~ and code `C++` and `{ "e": 1 }` and `[200, 404]`
bq. a quote line
h2. a heading line

> a quoted note

---

| a | b |
|---|---|
| c | d |

```python
x = 1
```

~~~
tilde fence
~~~""", """Goal: Probe two.
## Probe two
- Q1: lone plus C and caret x2 and tilde 30 and cite  here
- Q2: pairs x2 y^3 and 30 to 45 and a b ?? c and d  e + f
- Q3: image \\![](warning\\) and \\![](logo.png) and braces `name` and table a|b
- Q4: strike -gone- and code `C++` and `{ "e": 1 `} and `[200, 404]`
> a quote line
## a heading line
> a quoted note
----
|a|b|
|---|---|
|c|d|
```python
x = 1
```
tilde fence
~"""),
    ("""## Probe three

- R1: a lone bang! here
- R2: the form renders a <select> element
- R3: return List<String> from the method
- R4: see <https://example.com> and mail <ops@example.com>
- R5: comparators p95 < 300 ms and x >= 2

```
line one
line two
```""", """## Probe three
- R1: a lone bang! here
- R2: the form renders a  element
- R3: return List from the method
- R4: see  and mail
- R5: comparators p95 < 300 ms and x >= 2
```
line one
line two
```"""),
]
