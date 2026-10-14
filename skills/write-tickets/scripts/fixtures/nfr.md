<!-- expect errors=12 warnings=1 -->
# [E1] Keep sign-in responsive under load
Type: Epic
Blocked by: None
Jira:

## Goal
Sign-in stays usable at peak traffic.

## Success measures
- SM1: Sign-in returns 200 at peak traffic [children: S1, S2, T1]

## Non-functional requirements
- NFR1: Availability >= 99.9% per 30-day window [verify: out-of-band @ monthly uptime report]
- Uptime is high

## In scope
- The sign-in endpoint

## Out of scope
- Sign-up (not planned)

## Children
- S1, S2, T1

# [S1] Serve sign-in within its latency budget
Type: Story
Parent: E1
Blocked by: None
Handoff: signin-pr-01
Priority: Must
Jira:

## Context
Sign-in has no stated latency budget.

## Behavior
POST /auth/login answers within the budget below at peak traffic.

## Non-functional requirements
- NFR1: p95 response time < 300 ms at 200 requests/second [verify: automated @ tests/auth/login.test.ts]
- NFR2: p95 latency stays low at 200 requests/second [verify: out-of-band @ load test session 2]
- NFR3: Error rate < 0.1% over 24 hours of traffic
- p99 response time < 500 ms at 200 requests/second [verify: automated @ tests/auth/login.test.ts]
- NFR5: Cold start < 2 s on a 4-core runner [verify: automated @ tests/perf/coldstart.test.ts]
- NFR6: Search is fast, < 400 ms at 50 queries/second [verify: automated @ tests/auth/login.test.ts]
- NFR7: Memory < 512 MB at TBD sessions [verify: automated @ tests/auth/login.test.ts]
- NFR8: Sign-in stays responsive
- NFR9: Error rate stays low over 24 hours of traffic [verify: out-of-band @ weekly error report]
- NFR11: Throughput >= 1,000 requests/second at $5 per hour [verify: out-of-band @ load test report]
- NFR12: p99 response time ≤ 800 ms at 200 requests/second [verify: automated @ tests/auth/login.test.ts]
- NFR13: Cached lookup < .5 s at 10 requests/second [verify: automated @ tests/auth/login.test.ts]
- NFR14: Throughput >= 200 requests/second [verify:  @ load test report]

## Acceptance criteria
- AC1: POST /auth/login with valid credentials returns 200 [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): add the latency budget

## Out of scope
- Sign-up latency (not planned)

## Dependencies
- None

# [S2] Record the sign-in latency budget
Type: Story
Parent: E1
Blocked by: None
Handoff: signin-pr-02
Priority: Could
Jira:

## Context
The budget lives only in S1.

## Behavior
The budget is written next to the sign-in route.

## Non-functional requirements

## Acceptance criteria
- AC1: POST /auth/login returns 200 [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): note the budget

## Out of scope
- Other routes (not planned)

## Dependencies
- None

# [T1] Cache the sign-in user lookup
Type: Task
Parent: E1
Blocked by: S1
Handoff: signin-pr-01
Priority: Should
Jira:

## Context
Each sign-in reads the user row twice.

## Change
Read the user row once per sign-in.

## Non-functional requirements
- NFR1: p95 lookup time < 5 ms at 200 requests/second [verify: automated @ tests/auth/login.test.ts]

## Acceptance criteria
- AC1: A sign-in issues one user query [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): reuse the user row

## Out of scope
- Session caching (not planned)

## Dependencies
- S1: latency budget
