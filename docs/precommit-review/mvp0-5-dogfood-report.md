# MVP-0.5 Dogfood Report

Date: 2026-05-02

Branch: `codex-mvp0-review-console`

Frozen MVP-0 tag: `mvp0-review-console-v1`

Dogfood workspace: `/private/tmp/whether_commit_mvp05_dogfood`

This pass used a throwaway clone of the current project and exercised the real FastAPI routes against real staged and unstaged git states. The development worktree remained clean except for this report.

## Summary

MVP-0 is usable for the core staged review loop:

- Staged changes are captured.
- Medium-risk changes enter the review queue.
- Review state can clear review signals.
- Failed verification creates a blocker and returns `not_recommended`.
- Passing but target-misaligned verification remains review-gated.
- Staged-only snapshots remain non-stale when unrelated unstaged files change.
- Multi-hunk carryover preserved the unchanged hunk state and required review for the changed hunk.

The main reliability issue is verification alignment pollution from tool-owned local storage. Running verification creates `.precommit-review` files inside the repository, and those files are then treated as workspace changes outside the staged target. This makes otherwise clean verification runs look target-misaligned.

## Scenario Results

### Baseline: No Staged Changes

Result:

- Changed files: `0`
- Queue items: `0`
- Decision: `no_known_blockers`
- Message: `No pending staged changes.`

Assessment:

- Passed.
- The backend returns the expected empty staged-review state.

### Scenario 1: Small Staged Backend Change

Change:

- Added a small comment-only change to `backend/app/services/precommit_review/risk.py`.

Result:

- Changed files: `1`
- Queue items: `0`
- Decision: `no_known_blockers`
- Risk band: `low`
- Risk score: `20`
- Risk reasons: `No related test evidence`

Assessment:

- Partially passed.
- The staged file was captured and scored.
- No queue item was created because the file was low-risk.

Finding:

- The UI mental model says "review queue", but low-risk staged files do not appear in the queue. This may be acceptable, but the UI should make it clear that the queue contains unresolved review work, not every staged file.

### Scenario 2: High-Risk Backend Change

Change:

- Added a staged change to `backend/app/config/settings.py`.

Initial result:

- Changed files: `1`
- Queue items: `1`
- Decision: `needs_review`
- Risk band: `medium`
- Risk score: `45`
- Risk reasons: `Modifies config file`, `No related test evidence`
- Open signal: `unreviewed_high_risk_hunk`

After accepting risk:

- Queue items: `0`
- Decision: `no_known_blockers`
- Signal status: `accepted_risk`

Assessment:

- Passed.
- The risk reasons were understandable.
- `accepted_risk` clears user-resolvable review work as intended.

Follow-up:

- The UI should make the difference between user-resolvable review signals and system-only blockers visible before accepted risk becomes common in real use.

### Scenario 3: Staged Change with Unrelated Unstaged Edits

Change:

- Staged a small backend change.
- Added an unrelated unstaged doc file.

Result:

- Decision: `no_known_blockers`
- `stale=false`
- `workspace_changed_outside_target=true`

Assessment:

- Passed.
- Staged-only stale detection behaves correctly for unrelated unstaged user edits.

Follow-up:

- The UI banner should say that the staged assessment is still current, while the workspace has additional changes outside the review target.

### Scenario 4: Failed Verification Command

Change:

- Staged a small backend change.
- Ran a tool-launched command that exits with code `3`.

Verification result:

- Status: `failed`
- Exit code: `3`
- Display status: `executed_but_misaligned`
- `target_aligned=false`
- Raw output ref: `raw/command-output/run_*.txt`

Snapshot result:

- Decision: `not_recommended`
- Queue items: `1`
- Blocker signal: `failed_tool_launched_verification`

Assessment:

- Decision behavior passed.
- Raw output is stored outside the main snapshot payload.

Finding:

- Alignment did not pass. The run should have been aligned before any user-created unstaged change existed, but it was marked misaligned because `.precommit-review` storage itself changes the working tree outside the staged target.

### Scenario 5: Target-Misaligned Verification

Change:

- Staged a config change.
- Added an unrelated unstaged doc file.
- Ran a passing verification command.

Verification result:

- Status: `passed`
- Exit code: `0`
- Display status: `executed_but_misaligned`
- `target_aligned=false`

Snapshot result:

- Decision: `needs_review`
- Queue items: `2`
- Open signals:
  - `unreviewed_high_risk_hunk`
  - `target_misaligned_verification`

Assessment:

- Passed.
- Passing but misaligned verification stayed visible and did not clear the high-risk review requirement.

Finding:

- The behavior is correct for user-created unstaged changes, but it is currently confounded by the same `.precommit-review` storage issue from Scenario 4.

### Scenario 6: Multi-Hunk File Change

Change:

- Created two staged hunks in `backend/app/config/settings.py`.
- Marked both review signals as reviewed.
- Changed only the first hunk and rebuilt.

Initial result:

- Hunk count: `2`
- After review decision: `no_known_blockers`

After changing one hunk:

- Hunk count: `2`
- Decision: `needs_review`
- Signals:
  - Changed hunk signal: `open`
  - Unchanged hunk signal: `reviewed`

Assessment:

- Passed.
- The unchanged hunk carried review state across rebuild.
- The changed hunk required review again.

Finding:

- API consumers need to infer hunk state from signals. The hunk records themselves do not expose a visible `review_status`, and file records do not expose a per-file `review_state_summary`. This is workable for v1, but it makes UI rendering less direct.

## Findings

### False Positives

- None confirmed as product failures.
- `No related test evidence` appears on low-risk comment-only backend changes. It is understandable as a risk reason, but it may feel noisy if repeated on trivial changes.

### False Negatives

- Low-risk staged files can produce `no_known_blockers` without a queue item. This matches the current risk-gated queue behavior, but it may conflict with the expectation that every staged file appears in the review queue.

### UI Friction

- The queue is really an unresolved work queue, not a complete staged file queue. The UI should label it accordingly.
- Hunk review state is not directly visible on each hunk. After a hunk is reviewed, the signal status changes, but the hunk still appears as the same diff block with the same review action.
- `accepted_risk` is easy to apply from the signal list. The UI should distinguish user-resolvable review work from system-only blockers.

### Evidence Confusion

- Failed verification can display as `executed_but_misaligned` even when there was no user-created unstaged change. This is caused by tool-owned `.precommit-review` files being counted as outside-target workspace changes.
- The command text in verification messages can include absolute local paths, for example the full `.venv/bin/python` path. This is useful for traceability but should be considered sensitive in future redaction work.

### State Carryover Issues

- No blocker found in the tested multi-hunk flow.
- The unchanged hunk retained reviewed status, while the changed hunk became open again.
- The API would be easier to consume if hunk records included their effective review status.

### Privacy Concerns

- Raw command output is stored separately from `analysis.json`, which is the right direction.
- Raw output refs are stable local paths under `.precommit-review/raw/command-output/`.
- Verification signal messages include full command strings. Commands may include local paths, tokens, or other sensitive values. Redaction should happen before these messages are shown to users or sent to any future LLM context.

## Recommended Reliability Fixes

Priority order:

1. Exclude `.precommit-review` from staged-only workspace outside-target detection, or move tool-owned state outside the repository worktree.
2. Compute verification target alignment before writing raw output and verification SQLite state, then persist that alignment result with the run.
3. Add hunk-level effective review status to the read model so the UI can show reviewed, open, and accepted-risk states directly.
4. Rename or clarify "Review Queue" to "Unresolved Review Queue" if low-risk staged files remain outside the queue.
5. Redact or classify command strings before rendering verification messages.

## Exit Criteria Status

- At least 3 real review sessions completed: passed. Six dogfood scenarios plus the no-staged baseline were run against a throwaway clone of this repository.
- Blocker-level correctness issues fixed or documented: documented. The `.precommit-review` alignment pollution issue is the current top blocker.
- Risk scoring has no obvious severe misprioritization: mostly passed. The low-risk no-queue behavior needs product wording, not necessarily scoring changes.
- Stale and outside-target states are understandable in UI: partially passed. Backend behavior is correct for user changes, but tool-owned storage currently pollutes outside-target state.
- Hunk carryover works on real multi-hunk changes: passed for the tested config file flow.
- Raw command output storage reviewed for sensitive data risk: partially passed. Storage separation is good, but command string redaction is still needed.

## Next Step

Fix the verification alignment pollution first. Without that fix, dogfood users will see too many `executed_but_misaligned` verification runs, which weakens trust in one of MVP-0's core evidence signals.
