# Definition of Done — required before every `git commit`, no exceptions

Run in order. All must be green. Read this file before the first commit of a session; it
does not need re-reading between commits.

The commands are in `{{mechanics_gate_dod}}` — this file is the policy, that file is what
to run. Read both.

## The gate

1. **Format check, in lint mode**, so it reports rather than rewrites. Rewriting files
   mid-gate changes the tree you already staged, which is the same reason the pre-push gate
   rebases first: every step certifies a specific tree. Where a project has a separate
   fix command, run it before staging, never inside the gate.
2. **Lint, at CI's strictness.** A warning locally that is an error in CI is the single
   cheapest way to a red build. If the local invocation is not CI-identical, that is a
   defect in the mechanics file, not a reason to run something weaker.
3. **Delete stale result files BEFORE the run**, so a crashed run cannot leave the previous
   verdict behind for you to read as this one's.
4. **Unit tests.**
5. **Read the verdict from the result file**, never from the console or the exit code. An
   exit status routinely conflates a build failure with a test failure, and console output
   truncates.
6. **Dependency audit**, where the project has dependencies — unconditional, never
   conditional on whether they changed. Advisories land against versions already in the
   lockfile, so "nothing changed" is precisely when drift goes unnoticed until CI is red.
   The bar is zero advisories, with no allowlist, matching the pre-push gate.

**Network-dependent tests never gate a commit.** Integration tests that make live calls
stay opt-in: a commit gate that depends on a third party being up is a gate that fails for
reasons that have nothing to do with the diff.

## What this gate does not cover

Every project has behavior its local suite cannot reach. Steps 1–6 say nothing about it,
and a green run is not evidence for it. `{{failure_policy_gate}}` names that behavior and
the gate that covers it. Knowing which claim a green suite supports is the difference
between "the math is tested" and "the behavior is correct".

## Conditional gates

- **A suite CI deliberately skips** — run it locally at commit time. CI will not catch it,
  so this commit is the only place it gets caught.
- **A new source file** — prove the build system includes it. A file on disk the build
  does not enumerate is invisible to every gate above: it compiles nowhere, its tests never
  run, and the branch looks green because the code does not exist.
- **A new test file** — same check, plus confirm the class actually ran. A test the runner
  never discovered reports nothing rather than failing.
- **A user-facing string** — it goes through the localization API and reaches every locale.
  Parity is not optional: a key present in one locale and missing elsewhere renders the raw
  key to that user, and usually nothing fails when it does.
- **A lint or format config change** — re-run steps 1 and 2 over the whole repo, not just
  the diff. A rule change is repo-wide by definition, and a newly-enabled rule firing on
  untouched files turns the next commit red for reasons unrelated to it.
- **Changed markdown** — lint it, and check links when a link or its target moved.
- **Staged CI workflow files** — lint them. A workflow syntax error is otherwise only
  discoverable by pushing it, which is a slow way to find a typo. Invoke the linter by
  absolute path: `which` misses an install that is not on this shell's `PATH`, which reads
  as "not installed" when it is.
- **A comments-only commit** — prove it is comments-only rather than asserting it. Any
  non-comment hunk is a bug in the pass, fixed at its source rather than hand-patched.
- **A source comment added or changed** — it carries no work-item ID. The reason goes in
  the comment, one line, about the code; the ID goes in the commit message.
- **A guard's known false positives** — rephrase rather than suppress.

## Cross-cutting obligations — when you touch X, also touch Y

The gates above are commands. These are couplings: things that do not fail any command
until much later, or fail silently forever. Walk this table against the diff before
staging. A row whose left side appears in your diff and whose right side does not is either
a gap or a decision you must be able to state.

| You changed | You must also | Why it fails silently otherwise |
| --- | --- | --- |
| A pattern a hook should enforce | The hook **and** its self-test | A hook that does not know about a new pattern reports success. Self-tests assert finding _counts_, not exit status |
| Anything about what CI runs | The workflow **and** the job list in the pre-push gate | The gate that tells you what to run locally goes stale, so a CI job stops having a local equivalent |
| A new dependency | Check its license and transitive tree, run the audit, and re-resolve from scratch if you added an override | An incremental install silently ignores overrides for transitive dependencies |
| Behavior a user can see | The user-facing docs | Nothing verifies documentation; drift is only ever found by a reader |
| A test reading a file outside its own scope | Make an existing CI filter cover both sides | A guard pinning the other side never runs on the edit it exists to catch |

The project's own couplings are in `{{mechanics_gate_dod}}`. Neither table is exhaustive,
and a row is no substitute for thinking about the particular change. When you find a
coupling no table names, add the row.

## Domain subsystems — ask these of every change, not just the obvious one

Each is cross-cutting: it applies to work that is not "about" it, which is why it gets
missed. Answer each with a change or a reason it does not apply.

- **Localization.** Every user-facing string through the localization API, reaching every
  locale at matching positions.
- **Accessibility.** Interactive elements are reachable, carry an accessible name and a
  programmatic test locator, and announce async outcomes. Color alone never carries
  meaning. Text scales with the platform's dynamic type setting: a fixed text size or a
  fixed-height container holding text is a regression.
- **Failure modes of a new outbound call.** Every call needs a timeout, a decision about
  retry, and a stated failure behavior — the request fails, or it degrades. Never inside a
  transaction holding locks.

The project's domain list is in `{{mechanics_gate_dod}}`.

## Engineering practice — the questions no command asks

- **Persisted-state and deploy compatibility.** State written by the old version must
  survive the new one, and old code runs against a new schema during any rolling deploy. A
  renamed key silently resets every existing user's setting; a changed serialized shape
  makes a cached decode throw. Migrate, or state that a reset is acceptable and why.
  Renames and drops are two releases, never one.
- **Idempotency.** Anything retried must be safe to run twice. Retried deliveries,
  post-commit triggers, and fire-and-forget queueing all turn a non-idempotent handler into
  duplicate side effects rather than a recovered failure.
- **Secrets.** Encrypted at rest, never returned by an endpoint, never written to an audit
  entry or a log line. A new environment variable is documented and reaches every place
  that enumerates them.
- **Observability.** A new failure path a user can hit is logged with enough context to
  diagnose it. Never log a credential, a token, or a full request body.
- **Time.** Store UTC, compare in UTC, format in the viewer's zone.
- **Unsafe unwraps and casts.** A new one needs a stated reason it cannot fail, in one
  line, or it needs a guard.
- **Fixed constants are tuned values.** Changing one changes what the user sees; say what
  you measured, not what seemed better.
- **Pure functions get unit tests**, including the boundary cases. There is no excuse for
  verifying these by eye.
- **A new exported generic type or function gets a typed caller** in a typechecked file in
  the same commit. Called only from untyped tests, a variance error compiles unnoticed.

## Before `git add`

**Compare against the parent with `git worktree add` or `git show <ref>:<path>`, never
`git stash` and `stash pop` on a staged tree** — pop restores the working tree, not the
index, and the commit that follows is missing whatever was staged.

Read the diff and ask: does any block of logic appear more than once — within a file,
across files in this diff, or once here and once already in the repo? If yes, extract the
helper first, then stage.

Then read every comment the diff adds or changes. Cut any that restates the code, runs past
`CLAUDE.md`'s budget, or narrates a review round rather than describing the code — the
commit message is where history goes.

**A comment that moved is a comment to re-read.** Extracting a declaration leaves its
comment behind describing something no longer there, and carries assertions that were true
at the old site into a new one where they are not. Read every comment on both sides of a
move, not just the code.

**Renaming a symbol with `sed` or a regex rewrites prose too.** A bulk rename over a whole
file will happily rewrite the same word inside a comment or a string — it compiles, and only
a reader notices. Restrict the substitution to non-comment lines, or read every comment it
touched.

## After the commit — status report

A phase is not done at the commit. Report status before starting the next one; the format,
and the rules for reading `files`, duration, and AC evidence back from disk rather than from
memory, are in `status-report.md` beside this file.

## Reading results

Never rely on an exit code or a console summary for a test outcome. Delete stale result
files before the run, then read the generated file — `{{results_file}}`, with
`{{results_read_command}}`.

**Check the executed count, not just the failure count.** Zero failures out of forty
executed is not a pass of an eight-hundred-test suite — it is a run that died early. Compare
the total against the previous run's before believing a green verdict.

**If the output truncates, read the file — do not run the suite again** to get a cleaner
console. A second run is not more evidence than the first, and it costs minutes.
