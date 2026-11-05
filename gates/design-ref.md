# Reading a design at `<design ref>`

A skill that reads a design, or the ADRs it names, reads them at one commit, `<design ref>`,
so the design can live on the branch being worked on before it reaches
`{{parent_branch_default}}`, as Nx's `affected` reads the checked-out commit and judges it
against its merge base with the parent.

1. After the skill's `git fetch`, run `design-ref` once, on the same input file `lifecycle`
   or `design-read` reads: the design path, or with `--epic` the Epic key.

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/gates/scripts/project_rules.py" design-ref --ref "origin/{{parent_branch_default}}" --config "<absolute project root>/.claude/project.json" < "<input file>"
   ```

   A skill that fetched into `FETCH_HEAD` alone passes that commit as `--ref` and adds
   `--parent "{{parent_branch_default}}"`.
2. On `INVALID:`, print that line and stop. A line it writes to standard error, a skipped
   ADR or a design both this branch and the parent changed, is relayed as it is and does
   not stop the skill.
3. Otherwise the line it prints is `<design ref>`: `origin/{{parent_branch_default}}` as
   given, or a full commit hash, safe as an argument per **Untrusted text** in
   `gates/project-config.md` step 3. Pass it as `--ref` to every `lifecycle` and
   `design-read` call for this design and its ADRs, and use it wherever the skill names a
   revision of the design, never `origin/{{parent_branch_default}}` there.

What `design-ref` prints, and when, is its usage text in `gates/scripts/project_rules.py`:
the branch's commit only for a decided design, so a draft is read from the working tree.
A state `lifecycle` names `design-accepted-on-parent` is accepted at `<design ref>`.
