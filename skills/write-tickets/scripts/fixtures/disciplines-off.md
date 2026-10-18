<!-- expect -->
# [E1] Score churn risk on the sensor gateway
Type: Epic
Blocked by: None
Jira:

## Goal
The gateway flags accounts likely to churn within 30 days.

## Success measures
- SM1: Each account on the gateway carries a churn score [children: S1, S2, S3, S4, S5, S6, S7]

## Non-functional requirements
- NFR1: Gateway memory < 256 MB at 50 connected sensors in low power mode [verify: automated @ tests/auth/login.test.ts]
- NFR2: Score API availability >= 99.9% across regions [verify: out-of-band @ monthly uptime report]
- NFR4: Score API p99 latency < 400 ms over 1 day [verify: out-of-band @ monthly uptime report]
- NFR6: Score API availability >= 99.5% over 0 days [verify: out-of-band @ monthly uptime report]
- NFR5: Failover time < 30 s at 99.9% availability [verify: out-of-band @ monthly uptime report]
- NFR3: Score API p95 latency < 200 ms over 28 days [verify: out-of-band @ monthly uptime report]

## In scope
- Churn scores for accounts on the gateway

## Out of scope
- Scores for accounts off the gateway (not planned)

## Children
- S1, S2, S3, S4, S5, S6, S7

# [E2] Run the scoring model on battery power
Type: Epic
Blocked by: None
Jira:

## Goal
The gateway scores accounts for 8 hours on battery.

## Success measures
- SM1: A gateway on battery returns churn scores for 8 hours [children: S8, S9]

## Non-functional requirements
- NFR1: Model memory < 64 MB per loaded model [verify: automated @ tests/auth/login.test.ts]
- NFR2: Average power < 2 W while scoring [verify: out-of-band @ battery bench session]
- NFR3: Scoring timing jitter < 5 ms at 10 scores/second [verify: automated @ tests/auth/login.test.ts]

## In scope
- On-device scoring

## Out of scope
- Charging hardware (not planned)

## Children
- S8, S9

# [S1] Collect usage events for churn scoring
Type: Story
Parent: E1
Blocked by: None
Handoff: churn-pr-01
Priority: Must
Labels: data
Jira:

## Context
Churn scoring needs per-account usage events.

## Behavior
The gateway stores one usage event per account session.

## Acceptance criteria
- AC1: A finished session writes one row to `usage_events` [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): record the event

## Out of scope
- Event export (not planned)

## Dependencies
- None

# [S2] Store usage events for 90 days
Type: Story
Parent: E1
Blocked by: None
Handoff: churn-pr-01
Priority: Must
Labels: data
Jira:

## Context
Old usage events are kept forever today.

## Behavior
The gateway deletes usage events older than 90 days.

## Data
- Sources: gateway session logs
- Privacy: account IDs only, no names

## Acceptance criteria
- AC1: A nightly job deletes rows in `usage_events` older than 90 days [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): schedule the job

## Out of scope
- Archiving deleted rows (not planned)

## Dependencies
- None

# [S3] Hash account IDs in usage events
Type: Story
Parent: E1
Blocked by: None
Handoff: churn-pr-01
Priority: Must
Labels: data
Jira:

## Context
Usage events hold raw account IDs.

## Behavior
The gateway writes a salted hash in place of each account ID.

## Data
- Sources: gateway session logs
- Retention: none
- Privacy:

## Acceptance criteria
- AC1: A new row in `usage_events` holds a 64-character `account_hash` [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): hash before the write

## Out of scope
- Rehashing old rows (not planned)

## Dependencies
- None

# [S4] Join usage events to plan changes
Type: Story
Parent: E1
Blocked by: None
Handoff: churn-pr-02
Priority: Must
Labels: data
Jira:

## Context
Plan downgrades predict churn and live in a separate table.

## Behavior
Each usage event carries the account's current plan.

## Data
- Sources: gateway session logs, billing plan table
- Retention:
- Retention: 90 days
- Privacy: account hashes only

## Acceptance criteria
- AC1: A new row in `usage_events` holds the account's `plan_id` [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): look up the plan

## Out of scope
- Plan history (not planned)

## Dependencies
- None

# [S5] Train the first churn model
Type: Story
Parent: E1
Blocked by: None
Handoff: churn-pr-02
Priority: Must
Labels: model
Jira:

## Context
No churn model exists.

## Behavior
A training job writes a model file from the last 90 days of usage events.

## Acceptance criteria
- AC1: The training job writes `churn.onnx` to the model store [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): expose the training trigger

## Out of scope
- Scheduled retraining (not planned)

## Dependencies
- None

# [S6] Score accounts with the churn model
Type: Story
Parent: E1
Blocked by: None
Handoff: churn-pr-02
Priority: Must
Labels: model
Jira:

## Context
The model file is not yet served.

## Behavior
GET /churn/score returns the score for one account.

## Non-functional requirements
- NFR1: Recall >= 0.8 on the March sample [verify: automated @ tests/auth/login.test.ts]

## Acceptance criteria
- AC1: GET /churn/score for a known account returns 200 with a `score` field [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): register the route

## Out of scope
- Batch scoring (not planned)

## Dependencies
- None

# [S7] Calibrate churn scores
Type: Story
Parent: E1
Blocked by: None
Handoff: churn-pr-03
Priority: Must
Labels: model
Jira:

## Context
Raw scores are not probabilities.

## Behavior
GET /churn/score returns a calibrated probability.

## Non-functional requirements
- NFR1: Calibration error < 0.05 on holdout: [verify: automated @ tests/auth/login.test.ts]
- NFR2: Brier score < 0.2 on holdout: none [verify: automated @ tests/auth/login.test.ts]

## Acceptance criteria
- AC1: GET /churn/score returns a `score` between 0 and 1 [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): apply the calibration

## Out of scope
- Per-segment calibration (not planned)

## Dependencies
- None

# [S8] Score accounts on the gateway itself
Type: Story
Parent: E2
Blocked by: None
Handoff: churn-pr-03
Priority: Must
Labels: model
Jira:

## Context
Scoring runs in the cloud today.

## Behavior
The gateway loads the model file and scores accounts locally.

## Non-functional requirements
- NFR1: Recall >= 0.8 on holdout: churn-2026q3 [verify: automated @ tests/auth/login.test.ts]

## Acceptance criteria
- AC1: The gateway returns a `score` with the network disconnected [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): load the local model

## Out of scope
- Model updates over the air (not planned)

## Dependencies
- None

# [S9] Score accounts with the quantized model
Type: Story
Parent: E2
Blocked by: None
Handoff: churn-pr-03
Priority: Must
Labels: model
Jira:

## Context
The full model does not fit the gateway's memory budget.

## Behavior
The gateway scores accounts with an 8-bit quantized model.

## Non-functional requirements
- NFR1: Recall >= 0.78 on Holdout: `churn-2026q3` [verify: automated @ tests/auth/login.test.ts]

## Acceptance criteria
- AC1: The gateway loads `churn-int8.onnx` in place of `churn.onnx` [verify: automated @ tests/auth/login.test.ts]

## Touch points
- src/auth/routes.ts (modify): choose the quantized model

## Out of scope
- Quantizing other models (not planned)

## Dependencies
- None
