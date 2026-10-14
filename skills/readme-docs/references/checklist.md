# README quality checklist

## Must
- [ ] First paragraph says what the project is and what it's for, without jargon a newcomer wouldn't know.
- [ ] Install steps list prerequisites with versions that match manifests/CI.
- [ ] Quickstart commands were run in this session, or the report says why not.
- [ ] Example output is real (trimmed), not invented.
- [ ] License stated and matches the LICENSE file.
- [ ] No broken relative links (`scripts/check_readme.py` passes).
- [ ] No template placeholders left, except deliberate `<!-- TODO: confirm -->` comments listed in the report.
- [ ] File under 500 KiB (GitHub truncates beyond this).
- [ ] Exactly one H1; headings don't skip levels.

## Should
- [ ] Code blocks have language tags (`sh`, `python`, `text`, ...).
- [ ] README is under ~400 lines; longer material moved to docs/ and linked.
- [ ] Contributor-only content is in CONTRIBUTING.md, not the README.
- [ ] Project status (maturity / maintenance) is stated.
- [ ] Images are stored in the repo and have alt text.
- [ ] Badges, if any, resolve and reflect real CI/services.
- [ ] Terminology matches the codebase (same names for commands, modules, config keys).

## Avoid
- Marketing adjectives and unverifiable claims ("fastest", "production-ready") without evidence.
- Duplicating content that lives in another doc; link instead.
- Instructions that only work on the author's machine (absolute paths, personal aliases).
- Install steps copied from a similar project without checking this one.
