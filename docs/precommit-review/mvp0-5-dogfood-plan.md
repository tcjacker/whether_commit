# MVP-0.5 Dogfood & Reliability Pass

## Goal

Use real repository changes to validate whether the pre-commit review console helps developers review staged changes faster, more safely, and with clearer evidence.

This phase follows the completed MVP-0 Review Console on branch `codex-mvp0-review-console`, frozen by tag `mvp0-review-console-v1`.

Core MVP-0 commits:

- `95af7dd fix: decouple hunk review identity from file diff`
- `f64bb23 feat: add tool launched verification evidence`
- `45ddda5 feat: expose current precommit snapshot`
- `7f15faf feat: add precommit review console UI`

## Scope

This phase should not add new product surfaces unless required by dogfood findings. The goal is to harden the current review loop before moving to Python semantic evidence, agent context APIs, or additional language adapters.

Focus areas:

- Review queue usefulness.
- Risk score precision.
- Stale and outside-target messaging.
- Verification target alignment.
- Hunk state carryover stability.
- Raw command output privacy.
- UI friction during real review.

Out of scope:

- Python semantic evidence.
- Agent context API.
- TypeScript, Java, or Go semantic adapters.
- External agent log ingestion.
- Hosted or multi-user workflows.

## Dogfood Scenarios

### Scenario 1: Small Staged Backend Change

Validate:

- Queue ordering.
- Hunk review state.
- `no_known_blockers` path.

Expected outcome:

- The staged change enters the review queue.
- Reviewing the relevant hunk clears the review signal.
- The final decision can reach `no_known_blockers` when no blocker signals remain.

### Scenario 2: High-Risk Backend Change

Validate:

- Risk score reasons.
- `needs_review` behavior.
- `accepted_risk` behavior.

Expected outcome:

- High-risk files or hunks appear near the top of the queue.
- Risk reasons are understandable without reading implementation code.
- User-resolvable review signals can be resolved or accepted without clearing system-only blockers.

### Scenario 3: Staged Change with Unrelated Unstaged Edits

Validate:

- `stale=false`.
- `workspace_changed_outside_target=true`.
- UI clarity.

Expected outcome:

- The staged-only assessment remains current when unrelated unstaged content changes.
- The UI clearly shows that the workspace changed outside the review target.
- The banner does not imply that the staged review is stale.

### Scenario 4: Failed Verification Command

Validate:

- Failed command evidence.
- `not_recommended` decision.
- Raw output handling.

Expected outcome:

- A tool-launched command with a non-zero exit code creates failed verification evidence.
- The failed run creates a blocker signal.
- The final decision becomes `not_recommended`.
- Raw output is stored separately from the main snapshot payload.

### Scenario 5: Target-Misaligned Verification

Validate:

- Executed-but-misaligned label.
- High-risk blocker not cleared.

Expected outcome:

- A working-tree verification run against a staged-only target is marked misaligned when the working tree differs from the staged target.
- Passing but misaligned verification remains visible as executed evidence.
- Misaligned evidence cannot clear high-risk review requirements by itself.

### Scenario 6: Multi-Hunk File Change

Validate:

- Unchanged hunk review state carryover.
- Changed hunk re-review.
- Parent file partial review state.

Expected outcome:

- Review state carries over for unchanged hunk fingerprints after rebuild.
- Modified hunks require review again.
- The parent file is marked partially reviewed when only some hunks retain review state.

## Data to Record

For each run, record:

- Repository and branch.
- Review target.
- Number of changed files.
- Number of queue items.
- Final decision.
- False positives.
- False negatives.
- Confusing UI states.
- Risk score issues.
- Verification evidence issues.
- State carryover issues.
- Privacy concerns.
- Time to complete review.

## Finding Categories

Use these categories in the dogfood report:

- False positives: the system reported risk that did not matter for the commit.
- False negatives: the system missed a risk that the reviewer expected it to report.
- UI friction: the user got stuck, needed extra clicks, or could not tell what to do next.
- Evidence confusion: evidence labels or status text caused a wrong interpretation.
- State carryover issues: rebuild behavior preserved or invalidated review state incorrectly.
- Privacy concerns: raw output, paths, command text, or logs exposed sensitive information.

## Exit Criteria

MVP-0.5 is done when:

- At least 3 real review sessions are completed.
- All blocker-level correctness issues are either fixed or documented.
- Risk scoring has no obvious severe misprioritization.
- Stale and outside-target states are understandable in the UI.
- Hunk carryover works on real multi-hunk changes.
- Raw command output storage is reviewed for sensitive data risk.

## Report

Write the dogfood findings to:

```text
docs/precommit-review/mvp0-5-dogfood-report.md
```

The report should include outcome data for each scenario and grouped findings for false positives, false negatives, UI friction, evidence confusion, state carryover issues, and privacy concerns.
