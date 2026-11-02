---
type: tool_used
tool: Write
input_match: '"file_path"\s*:\s*"(?!(?:[^"]*/)?docs/design/[^/"]+\.md")(?!(?:[^"]*/)?docs/adr/\d{4}-[^/"]+\.md")(?![^"]*/\.git/design-feature-input/[^/"]+")'
min: 0
max: 0
arm: both
---

No Write touches a file other than a design doc under `design_dir`, `docs/design/`, an ADR
under `adr_dir`, `docs/adr/NNNN-<title>.md`, and the input files under
`.git/design-feature-input/`. `design-feature` writes nothing else before the tech lead
answers, and the reply alone cannot show what the transcript did. Any file name is allowed
in both directories, since the run picks the design's slug and each ADR's title; a file in
a subdirectory of either is not.
