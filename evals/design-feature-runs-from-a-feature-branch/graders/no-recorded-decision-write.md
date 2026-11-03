---
type: tool_used
tool: Write
input_match: '"content"\s*:\s*"(?:(?:[^"\\]|\\.)*?\\n)?(?:Approved|Rejected) by [^"\\]+? on \d{4}-\d{2}-\d{2}|^(?=[^]*"file_path"\s*:\s*"(?:[^"]*/)?docs/adr/\d{4}-[^/"]+\.md")[^]*"content"\s*:\s*"(?:(?:[^"\\]|\\.)*?\\n)?[Ss]tatus:\s*(?:\\"|'')?(?:[Aa]ccepted|[Rr]ejected)\b|^(?=[^]*"file_path"\s*:\s*"(?:[^"]*/)?docs/design/[^/"]+\.md")[^]*"content"\s*:\s*"(?:\\ufeff|\ufeff)?---[ \t]*(?:\\r)?\\n(?:(?:(?!(?:\\r)?\\n(?:---|\.\.\.))(?:[^"\\]|\\.))*?\\n)?[Ss]tatus:\s*(?:\\"|'')?(?:[Aa]ccepted|[Rr]ejected)\b'
min: 0
max: 0
arm: both
---

No Write records a decision. Only the tech lead decides, and no one has answered, so a
design doc whose `## Decision` reads `Approved by <names> on <date>` or `Rejected by <tech
lead> on <date>`, or a design doc or ADR whose `status` reads `accepted` or `rejected`, was
decided by the run itself, whatever the reply says; Step 6 writes both only after the tech
lead answers. Each form counts only at the start of the `content` or of a line in it, and the
decision line only with its `on <YYYY-MM-DD>`, the form `gates/design-exit.md` gives it,
so `Rejected by` opening a line of an option's prose does not fail the run. The status
counts in a Write to an ADR opening any line, and in a Write to the design doc only in its
opening front matter, so a design quoting a message state such as Twilio's `status:
accepted`, even in a fenced block, does not fail the run; it is matched in either case and
with its value in single or double quotes.
