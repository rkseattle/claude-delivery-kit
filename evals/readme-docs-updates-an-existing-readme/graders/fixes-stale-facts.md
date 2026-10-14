---
type: llm
---

`pyproject.toml` declares version 2.1.0 and `requires-python = ">=3.10"`. The old README
says "Requires Python 3.7+" and installs `notely==1.4`.

PASS when the updated README states a Python floor of 3.10 (or none) and does not pin
1.4 — that is, the old content was checked against the repo rather than carried over.

FAIL when the updated README still says Python 3.7 or still pins `notely==1.4`.
