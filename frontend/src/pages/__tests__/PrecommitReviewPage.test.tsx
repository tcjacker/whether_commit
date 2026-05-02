import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { PrecommitReviewPage } from '../PrecommitReviewPage'

const snapshot = {
  snapshot_id: 'pr_1',
  review_target: 'staged_only',
  decision: 'needs_review',
  stale: false,
  workspace_changed_outside_target: true,
  summary: { message: 'Pending staged changes require review.', changed_file_count: 1, review_state: 'unreviewed' },
  files: [{
    file_id: 'file_1',
    path: 'backend/schema.py',
    additions: 1,
    deletions: 1,
    review_state_summary: 'unreviewed',
    risk: { score: 50, band: 'high', reasons: [{ reason_id: 'schema', label: 'Schema changed', weight: 30 }] },
  }, {
    file_id: 'file_test',
    path: 'backend/tests/test_schema.py',
    additions: 2,
    deletions: 0,
    review_state_summary: 'reviewed',
    risk: { score: 5, band: 'low', reasons: [] },
  }],
  hunks: [{
    hunk_id: 'hunk_1',
    hunk_carryover_key: 'hunk_key_1',
    file_id: 'file_1',
    path: 'backend/schema.py',
    old_start: 1,
    old_lines: 1,
    new_start: 1,
    new_lines: 1,
    hunk_fingerprint: 'sha256:hunk',
    review_status: 'open',
    lines: [
      { type: 'header', content: '@@ -1 +1 @@' },
      { type: 'remove', content: 'value = 1' },
      { type: 'add', content: 'value = 2' },
    ],
  }, {
    hunk_id: 'hunk_test',
    hunk_carryover_key: 'hunk_key_test',
    file_id: 'file_test',
    path: 'backend/tests/test_schema.py',
    old_start: 1,
    old_lines: 0,
    new_start: 1,
    new_lines: 2,
    hunk_fingerprint: 'sha256:test-hunk',
    review_status: 'reviewed',
    lines: [
      { type: 'header', content: '@@ -0,0 +1,2 @@' },
      { type: 'add', content: 'def test_value():' },
      { type: 'add', content: '    assert True' },
    ],
  }],
  signals: [{
    signal_id: 'sig_1',
    kind: 'unreviewed_high_risk_hunk',
    target_type: 'hunk',
    target_id: 'hunk_1',
    severity: 'review',
    status: 'open',
    decision_impact: 'prevents_no_known_blockers',
    evidence_ids: ['run_1'],
    policy_rule_id: 'high_risk_hunk_unreviewed',
    message: 'backend/schema.py has a high-risk staged hunk that needs review.',
  }],
  queue: [{
    queue_id: 'sig_1',
    item_type: 'signal',
    target_id: 'hunk_1',
    status: 'open',
    message: 'backend/schema.py has a high-risk staged hunk that needs review.',
    priority: 50,
  }],
}

const reviewedSnapshot = {
  ...snapshot,
  decision: 'no_known_blockers',
  workspace_changed_outside_target: false,
  summary: { ...snapshot.summary, review_state: 'reviewed' },
  files: [{ ...snapshot.files[0], review_state_summary: 'reviewed' }],
  hunks: [{ ...snapshot.hunks[0], review_status: 'reviewed' }],
  signals: [{ ...snapshot.signals[0], status: 'reviewed' }],
  queue: [],
}

const api = vi.hoisted(() => ({
  fetchCurrentSnapshot: vi.fn(async () => snapshot),
  rebuildPrecommitReview: vi.fn(async () => snapshot),
  updateHunkReviewState: vi.fn(async () => reviewedSnapshot),
  fetchVerificationRun: vi.fn(async () => ({
    run_id: 'run_1',
    status: 'failed',
    exit_code: 1,
    display_status: 'executed',
    target_aligned: true,
    execution_mode: 'working_tree',
    raw_output_ref: 'raw/command-output/run_1.txt',
    command: '/Users/tc/private/bin/pytest --token=secret',
  })),
  runVerificationCommand: vi.fn(async () => ({
    run_id: 'run_1',
    status: 'failed',
    exit_code: 1,
    display_status: 'executed',
    target_aligned: true,
  })),
}))

vi.mock('../../api/precommitReview', () => api)

const assessmentManifest = {
    assessment_id: 'aca_ws_1',
    workspace_snapshot_id: 'ws_1',
    repo_key: 'demo',
    status: 'ready',
    mode: 'working_tree',
    provenance_capture_level: 'partial',
    mismatch_count: 1,
    weak_test_evidence_count: 1,
    review_decision: 'needs_tests',
    hunk_queue_preview: [{
      hunk_id: 'hunk_001',
      file_id: 'cf_abc123',
      path: 'backend/schema.py',
      priority: 92,
      risk_level: 'high',
      reasons: ['public API changed'],
      fact_basis: ['git_diff'],
      provenance_refs: [],
      mismatch_ids: ['mm_001'],
    }],
    agentic_summary: {
      generated_by: 'codex_logs',
      capture_level: 'partial',
      confidence: 'medium',
      time_window: { since_commit: 'HEAD', since_commit_time: null },
      user_design_goal: '用户希望保留提交分析。',
      codex_change_summary: 'Codex 建立 precommit review console。',
      main_objective: '保留顶部 Agentic Change Assessment，同时提供本地提交前审查。',
      key_decisions: [],
      files_or_areas_changed: [],
      tests_and_verification: ['pytest backend/tests'],
      unknowns: [],
    },
    summary: {
      headline: '本次变更包含提交前审查台更新。',
      overall_risk_level: 'medium',
      coverage_status: 'unknown',
      changed_file_count: 2,
      unreviewed_file_count: 1,
      affected_capability_count: 0,
      missing_test_count: 0,
      agent_sources: ['git_diff'],
      recommended_review_order: ['backend/schema.py'],
    },
    file_list: [],
    risk_signals_summary: [],
    agent_sources: ['git_diff'],
    review_progress: { total: 2, reviewed: 1, needs_follow_up: 0, needs_recheck: 0, unreviewed: 1 },
}

const assessmentApi = vi.hoisted(() => ({
  fetchLatestAssessment: vi.fn(),
  triggerAssessmentRebuild: vi.fn(),
}))

vi.mock('../../api/assessments', () => assessmentApi)

vi.mock('../../api/jobs', () => ({
  fetchJob: vi.fn(async () => ({
    job_id: 'job_1',
    repo_key: 'demo',
    status: 'success',
    step: 'done',
    progress: 100,
    message: 'done',
    created_at: '2026-05-02T00:00:00Z',
    updated_at: '2026-05-02T00:00:01Z',
  })),
}))

describe('PrecommitReviewPage', () => {
  afterEach(() => cleanup())

  beforeEach(() => {
    window.localStorage.clear()
    window.localStorage.setItem('precommit-review.language', 'en-US')
    api.fetchCurrentSnapshot.mockClear()
    api.rebuildPrecommitReview.mockClear()
    api.updateHunkReviewState.mockClear()
    api.fetchVerificationRun.mockClear()
    api.runVerificationCommand.mockClear()
    assessmentApi.fetchLatestAssessment.mockReset()
    assessmentApi.triggerAssessmentRebuild.mockReset()
    assessmentApi.fetchLatestAssessment.mockResolvedValue(assessmentManifest)
    assessmentApi.triggerAssessmentRebuild.mockResolvedValue({ job_id: 'job_1', status: 'pending' })
  })

  it('renders review console state and handles hunk review and verification run', async () => {
    render(<PrecommitReviewPage />)

    await waitFor(() => expect(screen.getAllByText('needs review').length).toBeGreaterThan(0))
    expect(await screen.findByLabelText('assessment-summary')).toBeInTheDocument()
    expect(screen.getByText('Agentic Change Assessment')).toBeInTheDocument()
    expect(screen.getByText('本次变更包含提交前审查台更新。')).toBeInTheDocument()
    expect(screen.getByText('代码变更总览')).toBeInTheDocument()
    expect(screen.getByText('Codex 聊天和操作记录')).toBeInTheDocument()
    expect(screen.getByText('测试执行情况')).toBeInTheDocument()
    expect(screen.getByText('Agent 总体评估')).toBeInTheDocument()
    expect(screen.getByLabelText('changed-files')).toBeInTheDocument()
    expect(screen.getByLabelText('file-diff')).toBeInTheDocument()
    expect(screen.getByLabelText('file-evidence')).toBeInTheDocument()
    expect(screen.getByText('Staged Files')).toBeInTheDocument()
    expect(within(screen.getByLabelText('changed-files')).getByText('backend/schema.py')).toBeInTheDocument()
    expect(within(screen.getByLabelText('changed-files')).queryByText('backend/tests/test_schema.py')).not.toBeInTheDocument()
    expect(screen.getByText('Unresolved Review Queue')).toBeInTheDocument()
    expect(screen.getByText('workspace changed outside target')).toBeInTheDocument()
    expect(screen.getAllByText('backend/schema.py').length).toBeGreaterThan(0)
    expect(screen.getAllByText('backend/schema.py has a high-risk staged hunk that needs review.').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: 'View evidence run_1' })).toBeInTheDocument()
    expect(screen.getByText('Hunk status: open')).toBeInTheDocument()
    expect(screen.getByText('value = 2')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'View evidence run_1' }))

    await waitFor(() => expect(api.fetchVerificationRun).toHaveBeenCalledWith('', 'run_1'))
    expect(await screen.findByText('Evidence run_1')).toBeInTheDocument()
    expect(screen.getByText('failed · exit 1 · aligned')).toBeInTheDocument()
    expect(screen.getByText('working_tree')).toBeInTheDocument()
    expect(screen.getByText('raw/command-output/run_1.txt')).toBeInTheDocument()
    expect(screen.queryByText('/Users/tc/private/bin/pytest --token=secret')).not.toBeInTheDocument()
    expect(screen.queryByText(/secret/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Mark hunk reviewed' }))

    await waitFor(() => expect(api.updateHunkReviewState).toHaveBeenCalledWith('', 'hunk_1', 'reviewed'))
    await waitFor(() => expect(screen.getAllByText('no known blockers').length).toBeGreaterThan(0))
    expect(screen.getByText('Hunk status: reviewed')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('verification command'), { target: { value: 'pytest' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run verification' }))

    await waitFor(() => expect(api.runVerificationCommand).toHaveBeenCalledWith('', 'pr_1', 'pytest'))
    await waitFor(() => expect(screen.getAllByText('failed · exit 1 · aligned').length).toBeGreaterThan(0))
  })

  it('preserves test management and language switching in the precommit console', async () => {
    render(<PrecommitReviewPage />)

    const precommitModules = await screen.findByLabelText('precommit modules')
    expect(within(precommitModules).getByRole('button', { name: 'Review' })).toBeInTheDocument()
    fireEvent.click(within(precommitModules).getByRole('button', { name: 'Tests' }))

    expect(screen.getByText('Test Files')).toBeInTheDocument()
    expect(within(screen.getByLabelText('changed-files')).getByText('backend/tests/test_schema.py')).toBeInTheDocument()
    expect(within(screen.getByLabelText('changed-files')).queryByText('backend/schema.py')).not.toBeInTheDocument()
    expect(screen.getByText('def test_value():')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '简体中文' }))

    expect(screen.getByText('测试文件')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '审查' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '测试' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('keeps a rebuildable agent assessment shell when the latest assessment is not ready', async () => {
    assessmentApi.fetchLatestAssessment.mockRejectedValueOnce(
      new Error('ApiError: ASSESSMENT_NOT_READY: Please trigger a rebuild first.'),
    )

    render(<PrecommitReviewPage />)

    expect(await screen.findByLabelText('assessment-summary')).toBeInTheDocument()
    expect(screen.getByText('Agentic Change Assessment')).toBeInTheDocument()
    expect(screen.getByText('Commit assessment is not ready. Please trigger a rebuild first.')).toBeInTheDocument()
    expect(screen.getByText('代码变更总览')).toBeInTheDocument()
    expect(screen.getByText('Codex 聊天和操作记录')).toBeInTheDocument()
    expect(screen.getByText('测试执行情况')).toBeInTheDocument()
    expect(screen.getByText('Agent 总体评估')).toBeInTheDocument()
    expect(screen.queryByText(/^ApiError:/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '开始重建' }))

    await waitFor(() => expect(assessmentApi.triggerAssessmentRebuild).toHaveBeenCalledWith({
      repo_key: 'divide_prd_to_ui',
      workspace_path: undefined,
    }))
  })
})
