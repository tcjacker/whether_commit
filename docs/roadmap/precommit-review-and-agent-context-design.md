# Pre-commit Review and Agent Context Design

## Thesis

This project should evolve into a local pre-commit review console backed by a language-aware code context layer for coding agents.

The review console is the product surface. It helps a developer decide whether a pending change is ready to commit. The code context layer is the durable technical base. It turns repository structure, AST entities, diffs, tests, and agent activity into evidence that both the UI and agents can query.

## Goals

- Provide a local quality gate before commit.
- Help reviewers inspect changed files in risk order.
- Explain each review signal with traceable evidence.
- Preserve reviewer decisions and follow-up state.
- Build a language-neutral semantic model that can support Python first, then TypeScript, Go, and Java.
- Expose structured context that an agent can use while editing, reviewing, or explaining code.

## Non-goals

- Do not build a full CI replacement in the first phase.
- Do not attempt complete compiler-grade understanding for every language.
- Do not add multi-user collaboration, permissions, or hosted storage yet.
- Do not make LLM summaries the source of truth.
- Do not support every language adapter before the core schema is stable.

## Product Direction

The first product direction is a pre-commit quality gate and AI-assisted review console.

The user flow should be:

1. A developer opens a local repository with pending changes.
2. The developer triggers a rebuild.
3. The backend captures the working tree, analyzes diffs, maps changes to code entities, gathers verification evidence, and builds an assessment.
4. The UI presents a clear decision: commit-ready, needs manual review, or not recommended to commit.
5. The developer reviews files in priority order.
6. For each file, the UI shows the diff, changed entities, related tests, evidence quality, risks, and agent reasoning.
7. The developer marks files as reviewed, needs follow-up, needs recheck, or false positive.
8. The final summary explains remaining blockers and produces a compact review checklist.

The second product direction is a code context layer for agents.

The agent-facing layer should answer questions such as:

- Which changed files are highest risk?
- Which changed entities lack executed test evidence?
- Which entrypoints or tests are related to this diff hunk?
- What did the agent claim to verify, and what evidence supports that claim?
- Which files should be reviewed before commit?

## Architecture Direction

The system should keep the current FastAPI backend and React frontend, but split the backend concepts more clearly:

- Capture layer: reads git status, diffs, untracked files, and workspace metadata.
- Language analysis layer: extracts entities, relations, entrypoints, and test facts from source code.
- Change mapping layer: maps diff hunks to language entities.
- Verification layer: records executed, inferred, claimed, missing, and unknown test evidence.
- Assessment layer: combines change, graph, verification, and agent activity into review signals.
- Review state layer: stores human decisions and notes separately from regenerated analysis.
- Query layer: serves both UI endpoints and future agent context endpoints.

The assessment layer should not depend on Python-specific AST shapes. Language adapters should emit the same intermediate schema.

## Semantic Model

The core model should be language-neutral:

- `CodeEntity`: a module, class, function, method, component, interface, type, route handler, job, or command.
- `Relation`: a dependency between entities, such as imports, calls, implements, extends, renders, routes_to, or tests.
- `Entrypoint`: a user-facing or system-facing execution boundary, such as an API route, CLI command, background job, UI route, or event handler.
- `ChangedEntity`: a code entity touched by a diff hunk, with path, line range, hunk id, and confidence.
- `TestEvidence`: evidence that a test is related to or executed for a change.
- `ReviewSignal`: a risk or confidence signal derived from change size, entity role, missing tests, weak evidence, or mismatched agent claims.
- `AgentActivity`: claimed actions from Codex, Claude, git-only fallback, or other local agent logs.

Adapters can add language-specific metadata, but the assessment builder should operate on these shared concepts.

## Language Roadmap

Python remains the reference adapter because the backend already has AST extraction and tests.

TypeScript should be the next adapter. It can be validated against the existing frontend codebase and is useful for component, route, hook, and API-client changes.

Go should follow TypeScript. Its standard AST tooling is stable, and test naming conventions are relatively analyzable.

Java should come after the shared model is proven. Java has high value, but Spring annotations, Maven and Gradle layouts, generated code, and interface-heavy call paths make it more expensive.

Each new language should ship only when it can produce useful review evidence through the shared schema. Full language coverage is less important than review-relevant coverage.

## MVP Scope

The first implementation phase should include:

- A clearer assessment decision: commit-ready, needs review, or do not commit yet.
- Review state persistence for each changed file.
- Evidence grades that distinguish executed, inferred, claimed, missing, and unknown verification.
- A stable review priority calculation.
- A language-neutral schema for code entities, changed entities, relations, entrypoints, test evidence, and review signals.
- Python adapter alignment with the new schema.
- Initial TypeScript adapter support for files, imports, functions, React components, hooks, and test files.
- UI changes that show decision, risk reason, evidence grade, and review state without hiding the diff.
- Agent context endpoints that expose the highest-risk files, weak evidence, changed entities, and review checklist.

## Deferred Scope

The following should wait until the MVP is reliable:

- Full Java and Go support.
- CI provider integrations.
- Hosted mode.
- Multi-user review collaboration.
- Historical trend dashboards.
- Large architecture diagrams.
- Automated commit creation or push flows.
- Broad LLM-generated architecture summaries.

## Data Flow

The rebuild flow should remain asynchronous:

1. Capture workspace snapshot.
2. Generate language graph snapshots.
3. Generate change analysis from git diff and diff hunk mapping.
4. Collect verification evidence.
5. Build review graph and assessment.
6. Save immutable analysis snapshots.
7. Preserve review state across compatible rebuilds when diff fingerprints match.

Review state should be stored separately from generated assessment data. Rebuilding analysis should not erase human review decisions unless the file diff fingerprint changes.

## Error Handling

The system should make partial results explicit.

- If a language adapter fails, the assessment should fall back to file-level diff review.
- If tests cannot be mapped, evidence should be marked unknown rather than missing.
- If an agent log cannot be read, the assessment should still use git diff evidence.
- If a rebuild fails, the UI should show the failed step and the last usable assessment if one exists.
- If review state cannot be carried forward, the UI should show that a re-review is required.

## Testing Strategy

Backend tests should cover:

- Schema validation for the language-neutral model.
- Python adapter output against representative source files.
- TypeScript adapter output against representative React and utility files.
- Diff hunk to entity mapping.
- Evidence grade calculation.
- Review decision calculation.
- Review state preservation across rebuilds.
- Agent context endpoint responses.

Frontend tests should cover:

- Assessment decision rendering.
- File priority ordering.
- Evidence grade display.
- Review state transitions.
- Rebuild progress and failure states.
- Empty and no-pending-change states.

End-to-end smoke tests should run the tool against this repository with known fixture changes.

## Milestones

### Milestone 1: Review Loop Hardening

Make the current assessment review flow usable for real local pre-commit review. Add durable review states, clearer decisions, better evidence labels, and failure handling.

### Milestone 2: Shared Semantic Model

Introduce the language-neutral entity and evidence schema. Refactor Python analysis output to conform to it while preserving current behavior.

### Milestone 3: TypeScript Adapter

Add TypeScript parsing for review-relevant facts: files, imports, exported functions, React components, hooks, API clients, and colocated tests.

### Milestone 4: Agent Context API

Expose structured query endpoints for agents. Start with highest-risk files, changed entities, weak evidence, and review checklist.

### Milestone 5: Broader Language Support

Add Go and Java only after the shared schema and agent query layer prove useful with Python and TypeScript.

## Success Criteria

The direction is working when:

- A developer can use the tool before commit and understand the remaining risk.
- Every major review signal has a visible evidence source.
- Rebuilds preserve useful human review state.
- Agents can query structured context instead of reading raw diffs alone.
- Adding TypeScript does not require a separate assessment pipeline.
- The project can evaluate its own backend and frontend changes with the same workflow.
