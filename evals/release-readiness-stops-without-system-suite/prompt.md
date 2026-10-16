---
description: release-readiness stops and names system_test_command when the project has no system suite, writing no summary
max_turns: 15
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Bash
  - Skill
tags:
  - guardrail
  - configuration
---

/delivery-kit:release-readiness 1.0.0
