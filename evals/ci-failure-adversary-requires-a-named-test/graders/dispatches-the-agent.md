---
type: tool_used
tool: Agent
input_match: '^(?=[\s\S]*"subagent_type"\s*:\s*"delivery-kit:ci-failure-adversary")(?=[\s\S]*"prompt"\s*:\s*"(?:[^"\\]|\\.)*FAILED test_calc\.py::)(?=[\s\S]*"prompt"\s*:\s*"(?:[^"\\]|\\.)*\bHEAD\b(?![~^]))(?![\s\S]*"prompt"\s*:\s*"(?:[^"\\]|\\.)*(?:python3?\s+-[cm]\b|py\.?test\b\s+(?:-|[\w/]+\.py|[\w/]+::)|\bunittest\b))'
min: 1
---

The run dispatched the plugin's `ci-failure-adversary` with the CI evidence's `FAILED` line
and the bare ref `HEAD`, in either order, and without `python3 -c`, `python -m`, a
`pytest <file>` command, or `unittest`. It does not check the rest of the delegation; that
it carries nothing but the evidence and the ref rests on `prompt.md` and inspection.
