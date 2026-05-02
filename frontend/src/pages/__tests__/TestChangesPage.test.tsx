import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TestChangesPage } from '../TestChangesPage'

vi.mock('../../api/assessments', () => ({
  fetchLatestAssessment: vi.fn(async () => ({
    assessment_id: 'aca_ws_1',
    workspace_snapshot_id: 'ws_1',
    repo_key: 'demo',
    status: 'ready',
    agentic_summary: {
      generated_by: 'codex_logs',
      capture_level: 'partial',
      confidence: 'medium',
      time_window: { since_commit: 'HEAD', since_commit_time: null },
      user_design_goal: '用户希望把 overview 改成 Agentic Change Assessment。',
      codex_change_summary: 'Codex 建立 diff review 工作台。',
      main_objective: '围绕 diff review 建立本轮变更评估闭环。',
      key_decisions: [],
      files_or_areas_changed: [],
      tests_and_verification: [],
      unknowns: [],
    },
    summary: {
      headline: '本次变更包含 2 个待审查文件。',
      overall_risk_level: 'low',
      coverage_status: 'unknown',
      changed_file_count: 2,
      unreviewed_file_count: 2,
      affected_capability_count: 0,
      missing_test_count: 0,
      agent_sources: ['git_diff'],
      recommended_review_order: ['backend/app/main.py', 'backend/tests/test_main.py'],
    },
    file_list: [
      {
        file_id: 'cf_app123',
        path: 'backend/app/main.py',
        old_path: null,
        status: 'modified',
        additions: 2,
        deletions: 1,
        risk_level: 'low',
        coverage_status: 'unknown',
        review_status: 'unreviewed',
        agent_sources: ['git_diff'],
        diff_fingerprint: 'sha256:app',
      },
      {
        file_id: 'cf_test123',
        path: 'backend/tests/test_main.py',
        old_path: null,
        status: 'modified',
        additions: 4,
        deletions: 0,
        risk_level: 'low',
        coverage_status: 'covered',
        review_status: 'unreviewed',
        agent_sources: ['git_diff'],
        diff_fingerprint: 'sha256:test',
      },
    ],
    risk_signals_summary: [],
    agent_sources: ['git_diff'],
    review_progress: { total: 2, reviewed: 0, needs_follow_up: 0, needs_recheck: 0, unreviewed: 2 },
  })),
  fetchAssessmentFileDetail: vi.fn(async () => ({
    file: {
      file_id: 'cf_test123',
      path: 'backend/tests/test_main.py',
      old_path: null,
      status: 'modified',
      additions: 4,
      deletions: 0,
      risk_level: 'low',
      coverage_status: 'covered',
      review_status: 'unreviewed',
      agent_sources: ['git_diff'],
      diff_fingerprint: 'sha256:test',
    },
    diff_hunks: [{
      hunk_id: 'hunk_001',
      old_start: 1,
      old_lines: 1,
      new_start: 1,
      new_lines: 2,
      hunk_fingerprint: 'sha256:def',
      lines: [{ type: 'add', content: 'assert response.status_code == 200' }],
    }],
    changed_symbols: [],
    related_agent_records: [],
    related_tests: [],
    impact_facts: [],
    file_assessment: {
      why_changed: 'No structured agent reason is available.',
      impact_summary: 'Review the diff.',
      test_summary: 'No direct test evidence was found.',
      recommended_action: 'Review this file manually.',
      generated_by: 'rules',
      agent_status: 'not_run',
      agent_source: null,
      confidence: 'low',
      evidence_refs: ['git_diff'],
      unknowns: ['Codex agent assessment has not run.'],
    },
    review_state: {
      review_status: 'unreviewed',
      diff_fingerprint: 'sha256:test',
      reviewer: null,
      reviewed_at: null,
      notes: [],
    },
  })),
}))

describe('TestChangesPage', () => {
  beforeEach(() => {
    window.localStorage.setItem('assessment.language', 'en-US')
  })

  it('renders only changed test files in the test module', async () => {
    render(<TestChangesPage />)

    expect(await screen.findByText('Test Files')).toBeInTheDocument()
    expect(screen.getAllByText('backend/tests/test_main.py').length).toBeGreaterThan(0)
    expect(screen.queryByText('backend/app/main.py')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/assert response.status_code/)).toBeInTheDocument())
  })
})
