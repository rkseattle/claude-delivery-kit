# Release readiness — the rule book's Phase 5 gate

Rule book Phase 5: "A release candidate ships only when every Must requirement passes its
acceptance tests and no open defect is rated Critical or High." Its exit criteria are the
four below, quoted from the rule book. `release-readiness` reads this file before it writes
a test summary's `Gate:` line, and checks every criterion against what that run read from
the results files, the suites' output, Jira, and `{{exceptions_log}}` — never against
memory of an earlier run.

## Exit criteria

- [ ] All Must acceptance tests pass
- [ ] Zero open Critical or High defects
- [ ] Non-functional thresholds met or exception recorded
- [ ] Test summary reviewed by product owner

## What settles each one

Before any suite runs, a `{{system_test_command}}`, `{{system_results_file}}`, or
`{{system_results_read_command}}` of `none` stops the run and names the key, and so does a
`{{system_results_file}}` equal to `{{results_file}}` or `{{integration_results_file}}`.
With any of those, there is no system verdict of this suite's own to read, as pre-push
step 6 stops for the integration suite. The release scope is the tickets `release-readiness`
Step 2 names: every `{{ticket_prefix}}` key in a commit subject since the latest `v*` tag
reachable from HEAD.
Descriptions are read in Markdown, with `jira_get_issue`, since a heading or `- NFR<n>:`
line searched for in stripped text is never found.

Every fact below is read by this run. A read that fails — a Jira call that errors or returns
only part of its results — fails each criterion that depends on it. A failed read never
counts as an empty list, since a list nobody could read would otherwise pass every check it
feeds. Jira answers "not found" both for a key that does not exist and for one the caller
may not see, so a scope key it reports as not found leaves the scope, listed under
`Known risks`, only when at least one other scope key read succeeded. That read shows
access, and the missing key is then a mistyped or deleted key in a subject nobody can
rewrite. With no scope key read, every not-found key is a failed read, and a scope left
empty after removals stops the run.

1. **All Must acceptance tests pass** — fails on any of:
   - `{{system_test_command}}` exits non-zero;
   - `{{system_results_file}}`, read with `{{system_results_read_command}}`, reports a
     failed test, or an executed count of zero, since a suite that ran nothing has not
     passed. The file is deleted before the command runs, as
     `${CLAUDE_PLUGIN_ROOT}/gates/pre-push.md` step 6 deletes its suite's, and read right
     after it, before any other suite runs. A file missing or unreadable afterward fails.
     No count read before that delete is ever used;
   - a ticket in the release scope carries the `moscow-must` label and its Jira status
     category is not `Done`;
   - an in-scope `moscow-must` ticket has no `## Acceptance criteria` heading, or no
     `- AC<n>:` line between it and the next heading: a Must requirement with no criteria
     has nothing to accept;
   - one of those lines carries no readable `[verify:]` tag, in the form
     `${CLAUDE_PLUGIN_ROOT}/skills/write-tickets/references/templates.md` defines and
     `write-tickets` writes, or the `\verify: …\` form Jira's Markdown conversion leaves of
     one written outside a code span; or its tag names a tier `{{verification_tiers}}` does
     not declare. With no tag, or an undeclared tier, no test is named for the criterion,
     and a requirement no one can test is not accepted (rule book Phase 2).

   Tiers stay the project's own: this gate maps none of them to a test level, and a
   criterion's suite counts say nothing about one criterion. No in-scope Must criterion is
   individually verified by this run, so `Untested requirements` lists every one, with its
   tier and evidence, together with each in-scope NFR with no result line and each case the
   two bullets above fail on, keyed by ticket and criterion, or by ticket alone when it has
   none. A listed criterion or NFR that does not fail a bullet above does not fail this
   criterion; the product owner accepts or returns it in criterion 4, the rule book's
   acceptance level.

   An executed count below the one in the previous release's summary, where
   `{{release_dir}}` holds it, is a risk the summary names, as pre-push step 5 asks. It
   does not fail the criterion: tests are removed for good reasons too.
2. **Zero open Critical or High defects** — fails on any issue of type Bug in
   `{{jira_project}}` whose status category is not `Done` and which carries
   `severity-critical` or `severity-high`. The type is Bug because it is the type
   `write-tickets` rates with a severity. The count is project-wide, not limited to the
   release scope: a severe defect is open whether or not this release's commits name it.
3. **Non-functional thresholds met or exception recorded** — fails on any in-scope NFR not
   met and not excepted.
   - **In scope** — each `- NFR<n>:` line under the `## Non-functional requirements`
     heading of an in-scope ticket or of its parent Epic, keyed `<KEY> NFR<n>` with that
     ticket's or Epic's key. Commits name Stories more often than Epics, and an Epic's
     thresholds hold for every release that changes its Stories.
   - **Met** — `{{nfr_test_command}}`, run with no arguments, printed exactly one line for
     the NFR, `<KEY> NFR<n> pass`. Anything else is a `fail` line: a `<KEY> NFR<n> fail`
     line, no line, a line in any other form, or both a `pass` and a `fail` line. An
     untested threshold is not a met one. Lines for NFRs outside the scope are ignored.
     The command's exit status is not read; its lines are. With `{{nfr_test_command}}`
     `none`, every in-scope NFR counts as a `fail` line.
   - **Excepted** — an unexpired `{{exceptions_log}}` row has a `Rule` reading exactly
     `<KEY> NFR<n>`. Expiry is as `${CLAUDE_PLUGIN_ROOT}/gates/exceptions.md` defines it.
     With `{{exceptions_log}}` `none`, no `fail` line is excepted.
4. **Test summary reviewed by product owner** — the summary's line before `Gate:` reads
   `Reviewed-by: product_owner <name> <YYYY-MM-DD>`, written only on
   `{{roles.product_owner}}`'s explicit answer. A relayed answer, as
   `${CLAUDE_PLUGIN_ROOT}/gates/project-config.md` defines one, names the person it came
   from and appends `, relayed by <git user.name>` after the date. A `Gate: FAIL` summary is
   reviewed the same way: the line records that the product owner saw the result, and it
   does not change the result. Anything but an explicit review writes nothing.

## The verdict

`Gate: PASS` when criteria 1 to 3 all hold, `Gate: FAIL` when any one fails. The line is
written before the review, so criterion 4 is never part of it. It is settled by the
`Reviewed-by:` line, which a release checks alongside `Gate: PASS`. A failing integration
suite, or an open Bug with no `severity-*` label, is reported in the summary and does not
change the verdict.
