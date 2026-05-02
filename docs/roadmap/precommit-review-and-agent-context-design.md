# Pre-commit Review Console Design

## 1. Product Thesis

This project should first become a local pre-commit review console. It should not replace CI, compile every language, or promise that a change is correct. It should answer a narrower question:

> Given the evidence collected for the current pending change, are there known blockers or unresolved review risks before commit?

The long-term technical direction remains a language-aware code context layer for agents, but that layer must grow from the review loop. The product surface validates which semantic facts are actually useful. The semantic layer then turns those facts into durable context for both reviewers and coding agents.

## 2. Review Target Semantics

Pre-commit review must define what is being reviewed. Git commits the index, not the whole working tree, so the system must make the target explicit.

| Target | Meaning | MVP default | Notes |
| --- | --- | --- | --- |
| `staged_only` | Review only staged changes that would enter the next commit. | Yes | This is the default pre-commit mode. |
| `working_tree_all` | Review staged, unstaged, and selected untracked files. | No | Useful for exploratory review before staging. |
| `staged_plus_unstaged` | Review tracked staged and unstaged changes, excluding untracked files by default. | No | Useful when users want one review before choosing staged hunks. |

Untracked files should be included only when the request sets `include_untracked=true`. The UI must label untracked evidence separately because untracked files are not part of a commit until staged.

The backend should capture two fingerprints: the selected review target and the wider workspace state. Stale analysis should be judged against the review target, not always against the full working tree.

```python
class ReviewTargetFingerprint(BaseModel):
    review_target: Literal["staged_only", "working_tree_all", "staged_plus_unstaged"]
    target_tree_hash: str
    included_paths_hash: str
    include_untracked: bool

class WorkspaceStateFingerprint(BaseModel):
    repo_head_sha: str
    index_tree_hash: str | None
    working_tree_fingerprint: str
    untracked_fingerprint: str | None
```

If the current `ReviewTargetFingerprint` differs from the snapshot fingerprint, the UI must show that the assessment is stale and require rebuild before returning `no_known_blockers`. In `staged_only` mode, unrelated unstaged edits should not stale the staged assessment unless they change the selected target or evidence alignment.

## 3. Decision Policy

The final decision is a policy result, not UI copy. The product should use conservative names that avoid overclaiming.

| Decision | Meaning |
| --- | --- |
| `no_known_blockers` | The collected evidence shows no blocking risk. Residual unknowns remain visible. |
| `needs_review` | The change may be acceptable, but unresolved review work or weak evidence remains. |
| `not_recommended` | A blocking condition exists, or the analysis is stale enough that the result cannot be trusted. |

Policy precedence is highest severity wins.

| Condition | Decision impact | Rationale |
| --- | --- | --- |
| Executed test evidence failed. | `not_recommended` | Known failing verification is a blocker. |
| Assessment target is stale relative to current index or working tree. | `not_recommended` | The analysis no longer describes the selected target. |
| Rebuild failed before producing a usable assessment. | `not_recommended` | The system cannot provide current evidence. |
| Supported-language adapter failed on a changed supported-language file. | At most `needs_review` | Fall back to file review, but do not claim no blockers. |
| High-risk hunk or signal remains unreviewed. | At most `needs_review` | Human review is still required. |
| Evidence is inferred-only for a high-risk file. | At most `needs_review` | The relationship is useful but not strong enough to clear risk. |
| Agent claimed verification with no matching execution evidence. | At most `needs_review` | Claims are not verification. |
| Large or cross-module change has no executed or inferred evidence. | At most `needs_review` | The system should surface uncertainty. |
| No failed evidence, no stale analysis, all high-risk items reviewed, and residual unknowns accepted. | `no_known_blockers` | The system found no blocker under current evidence. |

`no_known_blockers` must never mean "safe to merge" or "tests guarantee correctness." It means the local review gate found no known blocker.

The implementation should aggregate decisions from `ReviewSignal` records:

```python
class ReviewSignal(BaseModel):
    signal_id: str
    kind: str
    target_type: Literal["file", "hunk", "entity", "evidence", "claim", "snapshot"]
    target_id: str
    severity: Literal["info", "review", "blocker"]
    status: Literal["open", "resolved", "accepted_risk", "false_positive"]
    decision_impact: Literal[
        "none",
        "prevents_no_known_blockers",
        "forces_not_recommended",
    ]
    evidence_ids: list[str]
    policy_rule_id: str
    message: str
```

Decision aggregation:

```python
def decide(signals: list[ReviewSignal], snapshot_is_stale: bool) -> str:
    if snapshot_is_stale:
        return "not_recommended"
    open_signals = [s for s in signals if s.status == "open"]
    if any(s.decision_impact == "forces_not_recommended" for s in open_signals):
        return "not_recommended"
    if any(s.decision_impact == "prevents_no_known_blockers" for s in open_signals):
        return "needs_review"
    return "no_known_blockers"
```

## 4. Evidence Model

Evidence must carry provenance. Without source metadata, labels such as executed, inferred, or claimed are not trustworthy. Evidence also needs separate type, strength, and status fields so the UI can say, for example, "test run passed but target-misaligned" instead of collapsing that into "executed."

```python
class EvidenceSource(BaseModel):
    source_id: str
    source_type: Literal[
        "git_diff",
        "test_run",
        "coverage",
        "static_analysis",
        "agent_log",
        "user_review",
    ]
    repo_head_sha: str
    base_ref: str
    working_tree_fingerprint: str
    confidence: float
    command: str | None = None
    exit_code: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    tool_name: str | None = None
    tool_version: str | None = None
    raw_output_ref: str | None = None
```

```python
class Evidence(BaseModel):
    evidence_id: str
    evidence_type: Literal[
        "git_diff",
        "test_run",
        "static_relation",
        "coverage",
        "agent_claim",
        "user_review",
    ]
    strength: Literal["strong", "medium", "weak", "claim_only", "unknown"]
    status: Literal[
        "passed",
        "failed",
        "present",
        "missing",
        "unavailable",
        "stale",
        "misaligned",
    ]
    source_id: str
    confidence: float
```

Evidence types:

| Evidence type | Source | Strength | Invalidates when |
| --- | --- | --- | --- |
| `GitDiffEvidence` | `git_diff` | Strong for what changed, weak for correctness. | Target fingerprint changes. |
| `TestRunEvidence` | `test_run` | Strong when command, exit code, and target fingerprint match. | Target fingerprint or relevant test command changes. |
| `InferredRelationEvidence` | `static_analysis` | Medium or low depending on relation strength. | Adapter version, target fingerprint, or source entity fingerprint changes. |
| `CoverageEvidence` | `coverage` | Strong when tied to a current test run. | Test run or target fingerprint changes. |
| `AgentClaim` | `agent_log` | Claim only, not verification. | Agent log source changes or target fingerprint mismatch. |
| `UserReviewEvidence` | `user_review` | Strong for human acceptance of a hunk or signal. | Reviewed fingerprint changes. |

Agent claims must be modeled separately from execution evidence:

```python
class AgentClaim(BaseModel):
    claim_id: str
    source_id: str
    claim_type: Literal["ran_test", "inspected_file", "fixed_bug", "verified_behavior"]
    text: str
    related_files: list[str]
    related_commands: list[str]

class ClaimAssessment(BaseModel):
    claim_id: str
    status: Literal["supported", "contradicted", "unverified"]
    supporting_evidence_ids: list[str]
    notes: list[str]
```

The UI can show a claim, but only `TestRunEvidence` with matching command and exit code can prove execution.

Test execution must also be aligned with the review target. A test run on the full working tree does not necessarily prove that the staged tree passes.

```python
class TestRunEvidence(BaseModel):
    evidence_id: str
    command: str
    exit_code: int
    execution_mode: Literal["working_tree", "staged_tree", "clean_checkout", "unknown"]
    review_target_fingerprint: str
    execution_tree_fingerprint: str
    target_aligned: bool
```

If `target_aligned=false`, the evidence can be shown as an executed test run, but it cannot clear a high-risk blocker by itself.

## 5. Snapshot Model

Analysis output should be immutable. Review state should be separate and portable across compatible rebuilds.

```python
class AnalysisSnapshot(BaseModel):
    snapshot_id: str
    repo_path: str
    base_ref: str
    head_sha: str
    review_target: Literal["staged_only", "working_tree_all", "staged_plus_unstaged"]
    review_target_fingerprint: ReviewTargetFingerprint
    workspace_state_fingerprint: WorkspaceStateFingerprint
    created_at: datetime
    analysis_version: str
    adapter_versions: dict[str, str]
    status: Literal["running", "completed", "partial", "failed", "stale"]
```

The UI must display stale state whenever the current review target fingerprint differs from the snapshot. A stale snapshot can still be inspected, but it cannot produce `no_known_blockers`.

## 6. Review State Model

File-level review state is not enough. The system should preserve review decisions at the smallest stable review unit it can identify.

| State level | Purpose | Fingerprint |
| --- | --- | --- |
| `FileReviewState` | Tracks overall file disposition and notes. | File diff fingerprint. |
| `HunkReviewState` | Tracks whether a specific diff hunk was reviewed. | Normalized patch fingerprint, with nearest entity when available. |
| `SignalReviewState` | Tracks acceptance or dismissal of a risk, missing evidence item, or claim mismatch. | Signal kind, target stable id, evidence fingerprint set, and policy rule id. |

Review statuses:

- `unreviewed`
- `reviewed`
- `needs_follow_up`
- `needs_recheck`
- `false_positive`
- `accepted_risk`

Invalidation rules:

- Preserve `FileReviewState` only when the file diff fingerprint matches.
- Preserve `HunkReviewState` only when the hunk fingerprint matches.
- Preserve `SignalReviewState` only when the signal fingerprint and source evidence ids match.
- If a parent file changes but a hunk or signal fingerprint survives, keep the lower-level state and mark the file as partially reviewed.

This lets rebuilds avoid forcing a full file re-review when only one hunk changed.

## 7. MVP-0 Scope

MVP-0 is a Git-diff-only review console with enough evidence and state handling to validate the product loop.

| Capability | In MVP-0 | Explicitly deferred |
| --- | --- | --- |
| Pending change capture | `staged_only` default, optional working-tree modes. | Hosted repo analysis. |
| Diff display | File and hunk level. | Full semantic graph display. |
| Risk ordering | File and hunk heuristics from diff size, path type, deletion/addition mix, config/schema/test path hints. | Language-wide call graph risk. |
| Evidence model | Minimal evidence type, strength, status, provenance, and target alignment for git diff, tool-launched test runs, static path inference, and user review. | Coverage ingestion, external agent logs, and rich semantic evidence. |
| Review state | File, hunk, and signal state with fingerprint invalidation. | Multi-user review workflow. |
| Decision policy | `no_known_blockers`, `needs_review`, `not_recommended`. | Automated commit or push. |
| Stale detection | Required for selected review target. | Historical trend analysis. |
| UI loop | Show remaining files, unresolved hunks, weak evidence, and final decision. | Broad architecture diagrams. |

MVP-0 may use the existing Python adapter opportunistically, but it must not depend on a full semantic graph to be useful.

The main UI model should be a review queue, not only a file list. Queue items should include files, hunks, signals, stale snapshots, failed test evidence, weak evidence, and unsupported claims. The top-level status should summarize blockers, review items, and accepted unknowns.

MVP-0 should not read external Codex or Claude logs by default. It should use git diff and commands launched by this tool. Agent logs move to MVP-2 as an explicit opt-in input.

## 8. MVP-1 Python Semantic Evidence

MVP-1 introduces semantic evidence where the current backend is strongest.

Scope:

- Define the first version of `CodeEntity`, `ChangedEntity`, `Relation`, `Entrypoint`, and `TestEvidence`.
- Align the existing Python graph and change adapters with this schema.
- Map Python diff hunks to functions, classes, methods, FastAPI routes, schemas, jobs, and tests where available.
- Add relation strength:

```python
RelationStrength = Literal["direct", "static_inferred", "naming_convention", "agent_claimed"]
```

Adapter contract:

```python
class CodeEntity(BaseModel):
    entity_id: str
    language: Literal["python", "typescript", "go", "java"]
    kind: str
    path: str
    qualified_name: str
    display_name: str
    start_line: int
    end_line: int
    stable_fingerprint: str
    confidence: float
    metadata: dict[str, Any]
```

`entity_id` should not rely only on line numbers. It should combine language, path, qualified name, kind, and structural fingerprint so formatting changes do not destroy identity.

## 9. MVP-2 Agent Context API

Agent context should be a read-only facade over stable assessment data, not the same API used by the UI.

Two API facades should exist:

| API | Consumer | Contract |
| --- | --- | --- |
| `ReviewReadModelAPI` | UI | Stable, human-readable, paginated, low-noise. |
| `AgentContextAPI` | Coding agents | Structured, filterable, evidence-linked, machine-readable. |

MVP-2 should expose only high-signal queries:

- Highest-risk files.
- Unreviewed hunks.
- Weak or missing evidence.
- Changed entities.
- Agent claims with unsupported or contradicted status.
- Final review checklist.

The API must be read-only in this phase. Any endpoint that sends context to an external model should require explicit opt-in and redaction.

## 10. MVP-3 TypeScript / Vite React Adapter

TypeScript support should start as a narrow adapter for this repository's frontend shape, not a generic TypeScript adapter.

Name: `ViteReactAdapter v0`.

Initial supported paths:

- `frontend/src/components/**`
- `frontend/src/pages/**`
- `frontend/src/hooks/**`
- `frontend/src/api/**`
- `frontend/src/utils/**`
- `*.test.ts`
- `*.test.tsx`

Initial facts:

- Imports and exports.
- React component declarations.
- Hook declarations.
- API client functions.
- Test files and likely source-file relationship by path and naming convention.

Deferred TypeScript features:

- Next.js routing.
- React Router route extraction.
- Barrel export resolution beyond direct local files.
- Path alias resolution beyond configured Vite aliases.
- Dynamic import graph.
- Storybook, Playwright, Jest, and Vitest-specific evidence beyond simple test-file detection.

The adapter should graduate only after it produces useful review evidence for the current frontend without special-casing every file.

## 11. Error Handling and Partial Results

Partial results must affect the decision policy.

| Failure or partial state | User-visible behavior | Decision impact |
| --- | --- | --- |
| Language adapter fails on changed supported file. | Show file-level fallback and adapter error. | At most `needs_review`. |
| Test mapping unavailable. | Mark evidence as `unknown`, not `missing`. | High-risk files remain `needs_review`. |
| Agent log unavailable. | Show that agent evidence was not loaded. | No penalty by default. |
| Agent claim unsupported by execution evidence. | Show claim as unverified. | At most `needs_review`. |
| Rebuild fails before assessment. | Show failed step and last usable snapshot if available. | `not_recommended` for current target. |
| Snapshot stale. | Show stale banner and required rebuild. | `not_recommended` for current target. |
| Review state cannot be carried forward. | Mark affected items as needing re-review. | At most `needs_review`. |

The system should prefer explicit uncertainty over false confidence.

## 12. Security and Privacy

The MVP should remain local-first.

- No network upload in MVP-0.
- Do not read external agent logs by default in MVP-0.
- Raw command output and agent logs should be stored separately from summarized assessment fields.
- Secret redaction should run before any LLM summarization or external model call.
- Reading Codex or Claude logs should be explicit opt-in.
- Agent context endpoints should be read-only.
- Snapshot files should avoid embedding unnecessary raw secrets, tokens, customer data, or full command output.
- Future hosted mode must treat repo path, filenames, diffs, logs, and test output as sensitive data.

## 13. Test Plan

Backend tests:

- Review target selection for staged, working tree, and untracked files.
- Stale snapshot detection.
- Decision policy contract tests.
- Evidence provenance validation.
- Agent claim versus execution evidence matching.
- Review state preservation and invalidation at file, hunk, and signal level.
- Golden fixture tests for representative diffs and generated assessment JSON.
- Python semantic evidence mapping in MVP-1.
- Agent context endpoint contract tests in MVP-2.

Decision contract tests should include:

- Failed executed test returns `not_recommended`.
- Stale snapshot returns `not_recommended`.
- Adapter failure on changed supported file returns at most `needs_review`.
- Agent claimed test execution without matching command evidence returns at most `needs_review`.
- Inferred-only evidence on high-risk file returns at most `needs_review`.
- Reviewed high-risk items, no failed evidence, and no stale analysis can return `no_known_blockers`.

Frontend tests:

- Decision banner rendering.
- Stale assessment banner.
- Remaining review queue.
- File, hunk, and signal review state transitions.
- Evidence provenance display.
- Rebuild failure and last usable snapshot display.
- Empty and no-pending-change states.

End-to-end smoke tests should run this tool against this repository with fixed fixture changes.

## 14. Milestones

| Milestone | Focus | Exit criteria |
| --- | --- | --- |
| MVP-0 | Git diff review console. | A user can review staged changes, mark unresolved items, detect stale state, and get a conservative decision. |
| MVP-1 | Python semantic evidence. | Python changed entities and tests enrich review signals without breaking MVP-0. |
| MVP-2 | Agent context API. | Agents can query high-risk files, weak evidence, changed entities, and checklist data through read-only endpoints. |
| MVP-3 | Vite React adapter. | The current frontend produces useful component, hook, API, and test evidence. |
| Later | Go and Java adapters. | Shared schema and policy contracts already hold across Python and Vite React. |

## 15. Success Criteria

The design is working when:

- The review target is explicit and defaults to staged changes.
- The final decision follows a documented policy table.
- Every evidence item can explain its source, target fingerprint, and confidence.
- Review state survives compatible rebuilds and invalidates changed hunks or signals.
- Stale analysis is visible and cannot produce `no_known_blockers`.
- MVP-0 is useful without TypeScript, Go, Java, or a full semantic graph.
- Later semantic adapters improve the same review loop instead of creating a parallel product.
- A user can complete review for a staged diff with 10 changed files in under 5 minutes.
- Review state survives rebuild when no selected-target diff changes.
- Changing one hunk invalidates only that hunk or its parent file, not all files.
- Every final decision has at least one visible policy reason.
- `no_known_blockers` is never returned for stale snapshots or target-misaligned high-risk verification.

## Appendix A: Git Capture Protocol

MVP-0 must capture the selected target deterministically.

| Review target | Diff source | Tree hash source | Stale comparison |
| --- | --- | --- | --- |
| `staged_only` | `git diff --cached` | Index tree hash. | Current staged target fingerprint. |
| `working_tree_all` | `git diff HEAD` plus selected untracked files. | Working tree fingerprint. | Current tracked and included untracked fingerprint. |
| `staged_plus_unstaged` | Staged and unstaged tracked diffs. | Combined staged and unstaged tracked fingerprint. | Current tracked pending-change fingerprint. |

`ReviewTargetFingerprint` should include:

- `review_target`
- `base_ref`
- `repo_head_sha`
- `target_tree_hash`
- `included_paths_hash`
- `include_untracked`

`WorkspaceStateFingerprint` should include:

- `repo_head_sha`
- `index_tree_hash`
- `working_tree_fingerprint`
- `untracked_fingerprint`

The UI should show both:

- Target stale: selected review target changed and the assessment must be rebuilt.
- Workspace changed outside target: unstaged or untracked files changed, but the staged target may still be current.

## Appendix B: Evidence and Decision Algorithm

MVP-0 should create evidence only from sources it directly captures:

| Source | MVP-0 handling |
| --- | --- |
| Git diff | Strong evidence for changed files and hunks. |
| Tool-launched command | Strong test-run evidence when target-aligned. |
| Static path inference | Weak or medium evidence depending on rule confidence. |
| External agent log | Deferred to MVP-2. |
| User review action | Strong evidence for review disposition. |

Verification commands should be grouped into sessions:

```python
class VerificationSession(BaseModel):
    session_id: str
    snapshot_id: str
    created_by: Literal["user", "system", "agent"]
    commands: list[TestCommandRun]

class TestCommandRun(BaseModel):
    run_id: str
    command: str
    exit_code: int | None
    status: Literal["queued", "running", "passed", "failed", "error"]
    execution_mode: Literal["working_tree", "staged_tree", "clean_checkout", "unknown"]
    review_target_fingerprint: str
    execution_tree_fingerprint: str
    target_aligned: bool
    raw_output_ref: str | None
```

MVP-0 should offer explicit commands in the UI, such as `pytest`, `npm test`, and a custom command. Only commands launched by this tool create strong `TestRunEvidence`.

Decision algorithm:

1. Generate `ReviewSignal` records from stale state, failed evidence, target-misaligned verification, unresolved high-risk hunks, weak evidence, unsupported claims, and review state.
2. Mark signals resolved only when matching review state, successful aligned evidence, or explicit accepted risk exists.
3. Return `not_recommended` if any open signal forces it.
4. Return `needs_review` if any open signal prevents `no_known_blockers`.
5. Return `no_known_blockers` only when no open signal affects the decision.

## Appendix C: Fingerprint Specification

Fingerprint rules must be stable enough to preserve useful review state without hiding changed work.

File fingerprint:

- Review target.
- Path status: added, modified, deleted, renamed, untracked.
- Old path and new path.
- Normalized file patch content.

Hunk fingerprint v1:

- Old path and new path.
- Normalized added lines.
- Normalized removed lines.
- Patch-id-like hash of the hunk body.
- Nearest entity id when MVP-1 semantic data is available.

Signal fingerprint:

- `signal_kind`
- `target_type`
- `target_stable_id`
- Sorted evidence fingerprint set.
- `policy_rule_id`

UI message text must not participate in signal fingerprints. Copy changes should not invalidate review state.

Risk score:

```python
class RiskReason(BaseModel):
    reason_id: str
    label: str
    weight: int
    evidence_ids: list[str]

class RiskScore(BaseModel):
    score: int
    band: Literal["low", "medium", "high"]
    reasons: list[RiskReason]
```

MVP-0 risk rules:

| Rule | Weight |
| --- | ---: |
| Modifies config file. | +25 |
| Modifies schema or migration. | +30 |
| Modifies auth or permission path. | +35 |
| Deletes more lines than adds. | +10 |
| Large diff over 200 changed lines. | +20 |
| Touches tests only. | -10 |
| No related test evidence. | +20 |
| Untracked file included. | +10 |
| Lockfile changed. | +20 |
| Generated file suspected. | Warning, not score-clearing evidence. |

Risk bands:

- `low`: score below 25
- `medium`: score 25 to 49
- `high`: score 50 or above

## Appendix D: Local Storage Layout

MVP-0 should use JSON for immutable snapshots and raw artifacts, plus SQLite for mutable review state.

```text
.precommit-review/
  index.json
  snapshots/
    <snapshot_id>/
      analysis.json
      evidence/
        test-runs.jsonl
        user-review.jsonl
      raw/
        command-output/
  state.sqlite
```

Storage rules:

- `analysis.json` is immutable after a completed snapshot.
- Raw command output is stored by reference and can be redacted or garbage-collected.
- `state.sqlite` stores current review state keyed by repo, review target, file fingerprint, hunk fingerprint, and signal fingerprint.
- `index.json` points to the latest snapshot per review target.
- Garbage collection can remove raw outputs and old snapshots after configurable retention, but should keep review state unless the user clears it.
- Agent logs are not stored in MVP-0 because external agent log ingestion is deferred.

## Appendix E: MVP-0 API Contract

MVP-0 API endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/precommit-review/rebuild` | Capture selected target and build assessment snapshot. |
| `GET` | `/api/precommit-review/snapshots/current` | Return latest snapshot metadata and stale state for a review target. Returns `PRECOMMIT_REVIEW_NOT_READY` instead of rebuilding when no snapshot exists. |
| `GET` | `/api/precommit-review/queue` | Return prioritized review queue items. |
| `GET` | `/api/precommit-review/files` | Return changed files with risk and review state. |
| `GET` | `/api/precommit-review/files/{file_id}` | Return file detail, hunks, evidence, and signals. |
| `POST` | `/api/precommit-review/files/{file_id}/state` | Update file review state. |
| `POST` | `/api/precommit-review/hunks/{hunk_id}/state` | Update hunk review state. |
| `POST` | `/api/precommit-review/signals/{signal_id}/state` | Update signal review state. |
| `POST` | `/api/precommit-review/verification/run` | Start a tool-launched verification command. |
| `GET` | `/api/precommit-review/verification/runs/{run_id}` | Poll verification command status and evidence. |

MVP-2 agent context endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/agent-context/high-risk-files` | Machine-readable high-risk file list. |
| `GET` | `/api/agent-context/weak-evidence` | Weak, missing, stale, or misaligned evidence. |
| `GET` | `/api/agent-context/changed-entities` | Semantic changed entities after MVP-1. |
| `GET` | `/api/agent-context/review-checklist` | Remaining review checklist. |
| `GET` | `/api/agent-context/unsupported-claims` | Unsupported or contradicted agent claims. |

The UI should consume `ReviewReadModelAPI` endpoints. Agents should consume `AgentContextAPI` endpoints. They may share snapshots, but their API contracts should stay separate.
