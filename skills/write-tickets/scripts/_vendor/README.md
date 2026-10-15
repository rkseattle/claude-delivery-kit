# Vendored converter

`jira_roundtrip.py` checks a ticket description against the Atlassian MCP connector's own
write and read, so it needs nothing installed. The functions below are copied unchanged
from mcp-atlassian 0.21.0; the two wrappers named after them are the only code added here.

| Module | Copied unchanged | Source file SHA-256 |
| --- | --- | --- |
| `mcp_atlassian_adf.py` | `models/jira/adf.py`: `_parse_inline_formatting`, `_make_paragraph`, `_make_list_item`, `markdown_to_adf` | `e9f2966220b3a9786b2e3d3a5f707e17bd50e06cba1828d6e05fc137c58f7b58` |
| `mcp_atlassian_read.py` | `preprocessing/jira.py`: `_convert_panel`, and `JiraPreprocessor`'s `_process_mentions`, `_process_smart_links`, `jira_to_markdown`, `_convert_jira_list_to_markdown` | `46ab13be2077f2a121f3b557850ca69776e0dcacd7f4b722d320c0a759aa5b03` |
| `mcp_atlassian_read.py` | `preprocessing/base.py`: `_extract_blocks`, `_restore_blocks` | `e66bde72f848be55247d00331bd3eb24dc96af4db9d03e360677fb7383f3537e` |

Added here: `JiraReader`, a class holding the copied methods with the two attributes they
read; and `html_step_triggered`, the opening lines of `_convert_html_to_markdown` up to its
trigger test, copied unchanged into a function of their own. License: MIT, in
`LICENSE.mcp-atlassian`.

Not vendored, because it needs BeautifulSoup and markdownify 1.2.2: the rest of
`_convert_html_to_markdown`. `jira_roundtrip.py` models it and Jira's ADF-to-wiki rendering,
and its `PROBES` pin both to what Jira Cloud returned.

To upgrade, install the new release, check each source file's SHA-256 against this table to
see which changed, copy the same functions from it unchanged, update the version here and
in each module's docstring, and run `lint_draft.py --self-test`. Re-probe Jira when a probe
case fails.
