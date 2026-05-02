import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AssessmentReviewPage } from '../AssessmentReviewPage'

const assessmentApi = vi.hoisted(() => ({
  triggerFileAgentAssessment: vi.fn(),
}))

vi.mock('../../api/assessments', () => ({
  fetchLatestAssessment: vi.fn(async () => ({
    assessment_id: 'aca_ws_1',
    workspace_snapshot_id: 'ws_1',
    repo_key: 'demo',
    status: 'ready',
    mode: 'working_tree',
    provenance_capture_level: 'partial',
    mismatch_count: 1,
    weak_test_evidence_count: 1,
    review_decision: 'needs_tests',
    hunk_queue_preview: [
      {
        hunk_id: 'hunk_001',
        file_id: 'cf_abc123',
        path: 'backend/app/main.py',
        priority: 92,
        risk_level: 'high',
        reasons: ['public API changed', 'claimed tests have no execution evidence'],
        fact_basis: ['route_reference', 'no_execution_record'],
        provenance_refs: [],
        mismatch_ids: ['mm_001'],
      },
    ],
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
      headline: '本次变更包含 1 个待审查文件。',
      overall_risk_level: 'low',
      coverage_status: 'unknown',
      changed_file_count: 1,
      unreviewed_file_count: 1,
      affected_capability_count: 0,
      missing_test_count: 0,
      agent_sources: ['git_diff'],
      recommended_review_order: ['backend/app/main.py'],
    },
    file_list: [
      {
        file_id: 'cf_low123',
        path: 'frontend/vite.config.ts',
        old_path: null,
        status: 'modified',
        additions: 4,
        deletions: 1,
        risk_level: 'low',
        coverage_status: 'unknown',
        review_status: 'unreviewed',
        agent_sources: ['git_diff'],
        diff_fingerprint: 'sha256:low',
        highest_hunk_priority: 41,
        mismatch_count: 0,
        weakest_test_evidence_grade: 'inferred',
      },
      {
        file_id: 'cf_abc123',
        path: 'backend/app/main.py',
        old_path: null,
        status: 'modified',
        additions: 2,
        deletions: 1,
        risk_level: 'low',
        coverage_status: 'unknown',
        review_status: 'unreviewed',
        agent_sources: ['git_diff'],
        diff_fingerprint: 'sha256:abc',
        highest_hunk_priority: 92,
        mismatch_count: 1,
        weakest_test_evidence_grade: 'claimed',
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
    review_progress: { total: 1, reviewed: 0, needs_follow_up: 0, needs_recheck: 0, unreviewed: 1 },
  })),
  fetchAssessmentFileDetail: vi.fn(async () => ({
    file: {
      file_id: 'cf_abc123',
      path: 'backend/app/main.py',
      old_path: null,
      status: 'modified',
      additions: 2,
      deletions: 1,
      risk_level: 'low',
      coverage_status: 'unknown',
      review_status: 'unreviewed',
      agent_sources: ['git_diff'],
      diff_fingerprint: 'sha256:abc',
      highest_hunk_priority: 92,
      mismatch_count: 1,
      weakest_test_evidence_grade: 'claimed',
    },
    diff_hunks: [{
      hunk_id: 'hunk_001',
      old_start: 1,
      old_lines: 1,
      new_start: 1,
      new_lines: 2,
      hunk_fingerprint: 'sha256:def',
      lines: [{ type: 'add', content: 'new line' }],
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
    agent_claims: [
      {
        claim_id: 'claim_001',
        type: 'test',
        text: 'Codex said it added coverage for the changed route.',
        source: 'codex',
        session_id: 'sess_123',
        message_ref: 'assistant_msg_7',
        tool_call_ref: '',
        related_files: ['backend/app/main.py'],
        confidence: 'medium',
      },
    ],
    mismatches: [
      {
        mismatch_id: 'mm_001',
        kind: 'claimed_tested_but_no_executed_test_evidence',
        claim_id: 'claim_001',
        severity: 'high',
        explanation: 'Agent claimed test coverage, but no executed test evidence was found.',
        fact_refs: ['no_execution_record'],
        provenance_refs: [],
      },
    ],
    provenance_refs: [
      {
        source: 'codex',
        session_id: 'sess_123',
        message_ref: 'assistant_msg_7',
        tool_call_ref: 'apply_patch',
        command: '',
        file_path: 'backend/app/main.py',
        hunk_id: 'hunk_001',
        confidence: 'medium',
      },
    ],
    hunk_review_items: [
      {
        hunk_id: 'hunk_001',
        file_id: 'cf_abc123',
        path: 'backend/app/main.py',
        priority: 92,
        risk_level: 'high',
        reasons: ['public API changed', 'claimed tests have no execution evidence'],
        fact_basis: ['route_reference', 'no_execution_record'],
        provenance_refs: [],
        mismatch_ids: ['mm_001'],
      },
    ],
    review_state: {
      review_status: 'unreviewed',
      diff_fingerprint: 'sha256:abc',
      reviewer: null,
      reviewed_at: null,
      notes: [],
    },
  })),
  triggerFileAgentAssessment: assessmentApi.triggerFileAgentAssessment,
}))

describe('AssessmentReviewPage', () => {
  beforeEach(() => {
    window.localStorage.clear()
    assessmentApi.triggerFileAgentAssessment.mockReset()
    assessmentApi.triggerFileAgentAssessment.mockResolvedValue({
      file: {
        file_id: 'cf_abc123',
        path: 'backend/app/main.py',
        old_path: null,
        status: 'modified',
        additions: 2,
        deletions: 1,
        risk_level: 'low',
        coverage_status: 'unknown',
        review_status: 'unreviewed',
        agent_sources: ['git_diff'],
        diff_fingerprint: 'sha256:abc',
        highest_hunk_priority: 92,
        mismatch_count: 1,
        weakest_test_evidence_grade: 'claimed',
      },
      diff_hunks: [],
      changed_symbols: [],
      related_agent_records: [],
      related_tests: [],
      impact_facts: [],
      file_assessment: {
        why_changed: 'English reason.',
        impact_summary: 'English impact.',
        test_summary: 'English tests.',
        recommended_action: 'English action.',
        generated_by: 'codex_agent',
        agent_status: 'accepted',
        agent_source: 'codex',
        confidence: 'medium',
        evidence_refs: ['git_diff'],
        unknowns: [],
      },
      review_state: {
        review_status: 'unreviewed',
        diff_fingerprint: 'sha256:abc',
        reviewer: null,
        reviewed_at: null,
        notes: [],
      },
    })
  })

  afterEach(() => {
    cleanup()
  })

  it('renders summary, file list, diff, and evidence sections', async () => {
    render(<AssessmentReviewPage />)

    expect(await screen.findByText('本次变更包含 1 个待审查文件。')).toBeInTheDocument()
    expect(screen.getByText('代码变更总览')).toBeInTheDocument()
    expect(screen.getByText('Codex 聊天和操作记录')).toBeInTheDocument()
    expect(screen.getByText('测试执行情况')).toBeInTheDocument()
    expect(screen.getByText('Agent 总体评估')).toBeInTheDocument()
    expect(screen.getAllByText('backend/app/main.py').length).toBeGreaterThan(0)
    const changedFilesPanel = screen.getByLabelText('changed-files')
    expect(changedFilesPanel.textContent?.indexOf('backend/app/main.py')).toBeLessThan(
      changedFilesPanel.textContent?.indexOf('frontend/vite.config.ts') ?? Number.POSITIVE_INFINITY,
    )
    expect(screen.queryByText('backend/tests/test_main.py')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/new line/)).toBeInTheDocument())
    expect(screen.getByText('规则兜底')).toBeInTheDocument()
    expect(screen.getByText('结论')).toBeInTheDocument()
    expect(screen.getByText('Agent 声明')).toBeInTheDocument()
    expect(screen.getByText('不一致项')).toBeInTheDocument()
    expect(screen.getByText('测试证据')).toBeInTheDocument()
    expect(screen.getAllByText('溯源').length).toBeGreaterThan(0)
    expect(screen.getByText('working tree')).toBeInTheDocument()
    expect(screen.getByText('needs tests · 1 个不一致 · 1 个未审')).toBeInTheDocument()
    expect(screen.getByText(/暂不建议提交：需要补强测试证据后再提交。/)).toBeInTheDocument()
    expect(screen.getByText(/优先看 backend\/app\/main.py hunk_001 \(P92\)：public API changed/)).toBeInTheDocument()
    expect(screen.getByText('0 个缺失，1 个弱证据，覆盖 unknown')).toBeInTheDocument()
    expect(screen.getByText('捕获 partial，溯源 partial，置信度 medium')).toBeInTheDocument()
    expect(screen.getAllByText('优先级 92').length).toBeGreaterThan(0)
    expect(screen.getByText('claimed_tested_but_no_executed_test_evidence')).toBeInTheDocument()
    expect(screen.getByText('证据等级: claimed')).toBeInTheDocument()
    expect(screen.getByText(/sess_123/)).toBeInTheDocument()
  })

  it('switches the assessment UI to English', async () => {
    render(<AssessmentReviewPage />)

    fireEvent.click(await screen.findByRole('button', { name: 'English' }))

    expect(screen.getByText('Code Change Overview')).toBeInTheDocument()
    expect(screen.getByText('Codex Chat and Operation Records')).toBeInTheDocument()
    expect(screen.getByText('Test Execution')).toBeInTheDocument()
    expect(screen.getByText('Agent Overall Assessment')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Changed Files' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Run Codex Assessment' })).toBeInTheDocument()
    expect(window.localStorage.getItem('assessment.language')).toBe('en-US')
  })

  it('uses the selected language when running Codex assessment', async () => {
    render(<AssessmentReviewPage />)

    fireEvent.click(await screen.findByRole('button', { name: 'English' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Run Codex Assessment' }))

    await waitFor(() => expect(assessmentApi.triggerFileAgentAssessment).toHaveBeenCalled())
    expect(assessmentApi.triggerFileAgentAssessment).toHaveBeenCalledWith(
      'divide_prd_to_ui',
      'aca_ws_1',
      'cf_abc123',
      '',
      'en-US',
    )
  })
})
