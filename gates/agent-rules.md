# Agent rules — the project file every adversary agent reads

Each adversary agent in this plugin takes its project's rules from one file, named for
itself under `${CLAUDE_PROJECT_DIR}/.claude/agent-rules/`, at the path your definition
names. Read it before judging, and apply every rule in it.

If it does not exist, say so in one line and judge against whichever of the project's
`CLAUDE.md` and any fallback rules file your definition names exist — with none, against
the gates you read alone — inventing no rule to fill the gap: a fabricated rule is worse
than an absent one, because the author cannot tell it from a real finding. Your definition
says what else an absent file means.
