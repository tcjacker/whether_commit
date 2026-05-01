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

The backend should capture enough repository state to detect stale analysis:

```python
class WorkspaceFingerprint(BaseModel):
    repo_head_sha: str
    base_ref: str
    index_tree_hash: str | None = None
    working_tree_fingerprint: str
    review_target: Literal["staged_only", "working_tree_all", "staged_plus_unstaged"]
    include_untracked: bool
```

If the current target fingerprint differs from the snapshot fingerprint, the UI must show that the assessment is stale and require rebuild before returning `no_known_blockers`.

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

## 4. Evidence Model

Evidence must carry provenance. Without source metadata, labels such as executed, inferred, or claimed are not trustworthy.

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

## 5. Snapshot Model

Analysis output should be immutable. Review state should be separate and portable across compatible rebuilds.

```python
class AnalysisSnapshot(BaseModel):
    snapshot_id: str
    repo_path: str
    base_ref: str
    head_sha: str
    index_tree_hash: str | None = None
    working_tree_fingerprint: str
    review_target: Literal["staged_only", "working_tree_all", "staged_plus_unstaged"]
    created_at: datetime
    analysis_version: str
    adapter_versions: dict[str, str]
    status: Literal["running", "completed", "partial", "failed", "stale"]
```

The UI must display stale state whenever the current target fingerprint differs from the snapshot. A stale snapshot can still be inspected, but it cannot produce `no_known_blockers`.

## 6. Review State Model

File-level review state is not enough. The system should preserve review decisions at the smallest stable review unit it can identify.

| State level | Purpose | Fingerprint |
| --- | --- | --- |
| `FileReviewState` | Tracks overall file disposition and notes. | File diff fingerprint. |
| `HunkReviewState` | Tracks whether a specific diff hunk was reviewed. | Hunk content and line context fingerprint. |
| `SignalReviewState` | Tracks acceptance or dismissal of a risk, missing evidence item, or claim mismatch. | Signal type, target id, source evidence ids, and message fingerprint. |

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
| Evidence grades | Minimal: git diff, executed test command if available, inferred, claimed, missing, unknown. | Coverage ingestion and rich semantic evidence. |
| Review state | File, hunk, and signal state with fingerprint invalidation. | Multi-user review workflow. |
| Decision policy | `no_known_blockers`, `needs_review`, `not_recommended`. | Automated commit or push. |
| Stale detection | Required for selected review target. | Historical trend analysis. |
| UI loop | Show remaining files, unresolved hunks, weak evidence, and final decision. | Broad architecture diagrams. |

MVP-0 may use the existing Python adapter opportunistically, but it must not depend on a full semantic graph to be useful.

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
