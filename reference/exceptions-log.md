| Rule | Reason | Risk | Expiry | Remediation |
| ---- | ------ | ---- | ------ | ----------- |
| implement-phases Step 2c: `commit-adversary` review before every commit | Rob (tech lead) waived it for CDK-45 commit a69c1fb, a behavior-preserving switch of four scripts to shared helpers whose self-tests keep their case counts | A defect in that commit reaches the branch without a cold review | 2027-01-21 | `branch-review` reads the whole branch, a69c1fb included; at expiry, remove the row |
