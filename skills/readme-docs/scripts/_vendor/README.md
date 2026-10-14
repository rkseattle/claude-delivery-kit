# Vendored parser

`check_readme.py` parses Markdown with markdown-it-py, a pure-Python CommonMark parser, so
it needs nothing installed. The packages are copied unmodified from their wheels, minus
`markdown_it/cli`, the command-line entry point the checker does not use.

| Package | Version | License | Wheel SHA-256 |
| --- | --- | --- | --- |
| markdown-it-py | 3.0.0 | MIT (`markdown_it/LICENSE`, `markdown_it/LICENSE.markdown-it`) | `355216845c60bd96232cd8d8c40e8f9765cc86f46880e43a8fd22dc1a1a8cab1` |
| mdurl | 0.1.2 | MIT (`mdurl/LICENSE`) | `84008a41e51615a49fc9966191ff91509e3c40b939176e643fd50a5c2196b8f8` |

To upgrade, download both wheels with `pip download --no-deps`, check their hashes against
PyPI, replace these directories, and run `check_readme.py --self-test`.
