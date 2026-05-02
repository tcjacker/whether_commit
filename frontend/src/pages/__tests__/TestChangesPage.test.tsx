import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  analyzeAssessmentTestResult,
  fetchAssessmentTestCaseDetail,
  fetchAssessmentTests,
  fetchLatestAssessment,
} from '../../api/assessments'
import { TestChangesPage } from '../TestChangesPage'

vi.mock('../../api/assessments', () => ({
  analyzeAssessmentTestResult: vi.fn(async () => ({
    summary: 'Codex Agent analyzed 1 executed case and found the review signal scenario.',
    scenarios: [
      {
        title: 'Scenario named by test: test builder emits review signals.',
        source: 'generated',
        basis: ['codex_agent', 'test_name'],
      },
    ],
    test_data: ['Literal test data: needs_tests'],
    coverage_gaps: [],
    source: 'generated',
    basis: ['codex_agent', 'stored_run', 'test_code'],
  })),
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
      recommended_review_order: ['backend/app/schemas/assessment.py', 'backend/tests/test_builder.py'],
    },
    file_list: [
      {
        file_id: 'cf_schema',
        path: 'backend/app/schemas/assessment.py',
        old_path: null,
        status: 'modified',
        additions: 22,
        deletions: 4,
        risk_level: 'medium',
        coverage_status: 'covered',
        review_status: 'unreviewed',
        agent_sources: ['git_diff'],
        diff_fingerprint: 'sha256:schema',
      },
      {
        file_id: 'cf_tests',
        path: 'backend/tests/test_builder.py',
        old_path: null,
        status: 'modified',
        additions: 18,
        deletions: 1,
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
  fetchAssessmentTests: vi.fn(async () => ({
    assessment_id: 'aca_ws_1',
    repo_key: 'demo',
    changed_test_file_count: 1,
    test_case_count: 1,
    evidence_grade_counts: { direct: 1 },
    command_status_counts: { not_run: 1 },
    unknowns: [],
    files: [
      {
        file_id: 'tf_builder',
        path: 'backend/tests/test_builder.py',
        status: 'modified',
        additions: 18,
        deletions: 1,
        test_case_count: 1,
        strongest_evidence_grade: 'direct',
        weakest_evidence_grade: 'direct',
        latest_command_status: 'not_run',
        test_cases: [
          {
            test_case_id: 'tc_review_signals',
            file_id: 'tf_builder',
            path: 'backend/tests/test_builder.py',
            name: 'test_builder_emits_review_signals',
            status: 'modified',
            extraction_confidence: 'certain',
            evidence_grade: 'direct',
            weakest_evidence_grade: 'direct',
            last_status: 'not_run',
            covered_changes_preview: [
              {
                path: 'backend/app/schemas/assessment.py',
                hunk_id: 'hunk_review_signal_schema',
                risk_level: 'medium',
                evidence_grade: 'direct',
              },
            ],
            highest_risk_covered_hunk_id: 'hunk_review_signal_schema',
            intent_summary: {
              text: 'Ensures the test builder emits review signals.',
              source: 'rule_derived',
              basis: ['test name mentions review signals', 'assertions inspect result payload'],
            },
          },
          {
            test_case_id: 'tc_command_paths',
            file_id: 'tf_builder',
            path: 'backend/tests/test_builder.py',
            name: 'test_builder_emits_command_paths',
            status: 'modified',
            extraction_confidence: 'certain',
            evidence_grade: 'direct',
            weakest_evidence_grade: 'direct',
            last_status: 'not_run',
            covered_changes_preview: [
              {
                path: 'backend/app/schemas/assessment.py',
                hunk_id: 'hunk_command_paths_schema',
                risk_level: 'low',
                evidence_grade: 'direct',
              },
            ],
            highest_risk_covered_hunk_id: 'hunk_command_paths_schema',
            intent_summary: {
              text: 'Ensures the test builder emits command paths.',
              source: 'rule_derived',
              basis: ['test name mentions command paths', 'assertions inspect command payload'],
            },
          },
        ],
      },
    ],
  })),
  fetchAssessmentTestCaseDetail: vi.fn(async () => ({
    test_case: {
      test_case_id: 'tc_review_signals',
      file_id: 'tf_builder',
      path: 'backend/tests/test_builder.py',
      name: 'test_builder_emits_review_signals',
      status: 'modified',
      extraction_confidence: 'certain',
      evidence_grade: 'direct',
      weakest_evidence_grade: 'direct',
      last_status: 'not_run',
      covered_changes_preview: [
        {
          path: 'backend/app/schemas/assessment.py',
          hunk_id: 'hunk_review_signal_schema',
          risk_level: 'medium',
          evidence_grade: 'direct',
        },
      ],
      highest_risk_covered_hunk_id: 'hunk_review_signal_schema',
      intent_summary: {
        text: 'Ensures the test builder emits review signals.',
        source: 'rule_derived',
        basis: ['test name mentions review signals', 'assertions inspect result payload'],
      },
    },
    diff_hunks: [
      {
        hunk_id: 'test_hunk_1',
        old_start: 20,
        old_lines: 2,
        new_start: 20,
        new_lines: 4,
        hunk_fingerprint: 'sha256:test-hunk',
        lines: [
          { type: 'context', content: 'result = build_test_management_summary(change_set)' },
          { type: 'add', content: 'assert result' },
        ],
      },
    ],
    full_body: [
      { type: 'context', content: 'def test_builder_emits_review_signals():' },
      { type: 'context', content: '    result = build_test_management_summary(change_set)' },
      { type: 'add', content: '    assert result' },
    ],
    assertions: [
      { type: 'add', content: 'assert result' },
    ],
    covered_scenarios: [
      {
        title: 'Scenario named by test: test builder emits review signals.',
        source: 'rule_derived',
        basis: ['test_name'],
      },
    ],
    test_results: [
      {
        run_id: 'run_builder',
        source: 'rerun',
        command: 'uv run pytest backend/tests/test_builder.py',
        status: 'passed',
        exit_code: 0,
        duration_ms: 321,
        stdout: 'backend/tests/test_builder.py::test_builder_emits_review_signals PASSED',
        stderr: '',
        executed_cases: [
          {
            node_id: 'backend/tests/test_builder.py::test_builder_emits_review_signals',
            name: 'test_builder_emits_review_signals',
            status: 'passed',
            source: 'collect_only',
            scenarios: [],
            test_data: [],
          },
        ],
        analysis: {
          summary: '1 test case was associated with this run.',
          scenarios: [],
          test_data: [],
          coverage_gaps: [],
          source: 'rule_derived',
          basis: ['runner_output', 'collect_only'],
        },
        captured_at: '2026-04-26T00:00:00Z',
        evidence_grade: 'direct',
      },
    ],
    covered_changes: [
      {
        path: 'backend/app/schemas/assessment.py',
        symbol: 'TestCaseSummary',
        hunk_id: 'hunk_review_signal_schema',
        relationship: 'asserts_behavior',
        evidence_grade: 'direct',
        basis: ['assertion validates result payload'],
      },
    ],
    recommended_commands: [
      {
        command_id: 'cmd_builder',
        command: 'uv run pytest backend/tests/test_builder.py',
        reason: 'Run the changed builder test.',
        scope: 'test_case',
        status: 'not_run',
        last_run_id: null,
      },
    ],
    related_agent_claims: [],
    unknowns: [],
  })),
  triggerAssessmentRebuild: vi.fn(async () => ({
    job_id: 'job_1',
    repo_key: 'demo',
    status: 'success',
    step: 'complete',
    progress: 1,
    message: 'done',
    created_at: '2026-04-26T00:00:00Z',
    updated_at: '2026-04-26T00:00:00Z',
  })),
}))

function testCaseDetailFixture(testCaseId: string, name: string, assertion: string) {
  return {
    test_case: {
      test_case_id: testCaseId,
      file_id: 'tf_builder',
      path: 'backend/tests/test_builder.py',
      name,
      status: 'modified' as const,
      extraction_confidence: 'certain' as const,
      evidence_grade: 'direct' as const,
      weakest_evidence_grade: 'direct' as const,
      last_status: 'not_run' as const,
      covered_changes_preview: [
        {
          path: 'backend/app/schemas/assessment.py',
          hunk_id: 'hunk_review_signal_schema',
          risk_level: 'medium' as const,
          evidence_grade: 'direct' as const,
        },
      ],
      highest_risk_covered_hunk_id: 'hunk_review_signal_schema',
      intent_summary: {
        text: 'Ensures the test builder emits review signals.',
        source: 'rule_derived' as const,
        basis: ['test name mentions review signals', 'assertions inspect result payload'],
      },
    },
    diff_hunks: [
      {
        hunk_id: 'test_hunk_1',
        old_start: 20,
        old_lines: 2,
        new_start: 20,
        new_lines: 4,
        hunk_fingerprint: 'sha256:test-hunk',
        lines: [
          { type: 'context' as const, content: 'result = build_test_management_summary(change_set)' },
          { type: 'add' as const, content: assertion },
        ],
      },
    ],
    full_body: [
      { type: 'context' as const, content: `def ${name}():` },
      { type: 'add' as const, content: `    ${assertion}` },
    ],
    assertions: [
      { type: 'add' as const, content: assertion },
    ],
    covered_scenarios: [
      {
        title: `Scenario named by test: ${name.replaceAll('_', ' ')}.`,
        source: 'rule_derived' as const,
        basis: ['test_name'],
      },
    ],
    test_results: [
      {
        run_id: `run_${testCaseId}`,
        source: 'rerun' as const,
        command: 'uv run pytest backend/tests/test_builder.py',
        status: 'passed' as const,
        exit_code: 0,
        duration_ms: 321,
        stdout: `${name} PASSED`,
        stderr: '',
        executed_cases: [
          {
            node_id: `backend/tests/test_builder.py::${name}`,
            name,
            status: 'passed' as const,
            source: 'collect_only' as const,
            scenarios: [],
            test_data: [],
          },
        ],
        analysis: {
          summary: `${name} result summary`,
          scenarios: [],
          test_data: [],
          coverage_gaps: [],
          source: 'rule_derived' as const,
          basis: ['runner_output'],
        },
        captured_at: '2026-04-26T00:00:00Z',
        evidence_grade: 'direct' as const,
      },
    ],
    covered_changes: [
      {
        path: 'backend/app/schemas/assessment.py',
        symbol: 'TestCaseSummary',
        hunk_id: 'hunk_review_signal_schema',
        relationship: 'names_changed_symbol' as const,
        evidence_grade: 'direct' as const,
        basis: ['assertion validates result payload'],
      },
    ],
    recommended_commands: [
      {
        command_id: 'cmd_builder',
        command: 'uv run pytest backend/tests/test_builder.py',
        reason: 'Run the changed builder test.',
        scope: 'test_case' as const,
        status: 'not_run' as const,
        last_run_id: null,
      },
    ],
    related_agent_claims: [],
    unknowns: [],
  }
}

describe('TestChangesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.setItem('assessment.language', 'en-US')
  })
  afterEach(() => cleanup())

  it('renders test cases with result, covered changed code, and commands', async () => {
    render(<TestChangesPage />)

    expect(await screen.findByText('Test Cases')).toBeInTheDocument()
    expect(screen.getAllByText('test_builder_emits_review_signals').length).toBeGreaterThan(0)
    await waitFor(() => expect(screen.getByText('Test Result')).toBeInTheDocument())
    expect(screen.getByText('1 test case was associated with this run.')).toBeInTheDocument()
    const resultPanel = screen.getByRole('main', { name: 'test-result' })
    const resultHeadings = within(resultPanel).getAllByRole('heading').map(heading => heading.textContent)
    expect(resultHeadings.indexOf('Rule Analysis')).toBeLessThan(resultHeadings.indexOf('Executed Cases'))
    expect(screen.getByText('backend/app/schemas/assessment.py')).toBeInTheDocument()
    expect(screen.getByText('uv run pytest backend/tests/test_builder.py')).toBeInTheDocument()

    expect(fetchLatestAssessment).toHaveBeenCalledWith('divide_prd_to_ui', '')
    expect(fetchAssessmentTests).toHaveBeenCalledWith('divide_prd_to_ui', 'aca_ws_1', '')
    expect(fetchAssessmentTestCaseDetail).toHaveBeenCalledWith(
      'divide_prd_to_ui',
      'aca_ws_1',
      'tc_review_signals',
      '',
    )
  })

  it('lazy-loads test result agent analysis from the selected stored run and closes the progress modal', async () => {
    render(<TestChangesPage />)

    await waitFor(() => expect(screen.getByRole('button', { name: 'Agent Analyze' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Agent Analyze' }))

    await waitFor(() => {
      expect(analyzeAssessmentTestResult).toHaveBeenCalledWith(
        'divide_prd_to_ui',
        'aca_ws_1',
        'tc_review_signals',
        'run_builder',
        '',
      )
    })
    expect(screen.queryByRole('dialog', { name: 'Agent test result analysis' })).not.toBeInTheDocument()
  })

  it('switches the test management page copy to Chinese', async () => {
    render(<TestChangesPage />)

    fireEvent.click(await screen.findByRole('button', { name: '简体中文' }))

    expect(screen.getByRole('heading', { name: 'AI 编写的测试用例' })).toBeInTheDocument()
    expect(screen.getByText('测试管理')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '测试用例' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('heading', { name: '测试结果' })).toBeInTheDocument())
    expect(screen.getByRole('heading', { name: '测试意图' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agent 分析' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重新运行' })).toBeInTheDocument()
    expect(window.localStorage.getItem('assessment.language')).toBe('zh-CN')
  })

  it('does not render stale detail after switching test cases', async () => {
    let resolveFirstDetail: (value: ReturnType<typeof testCaseDetailFixture>) => void = () => {}
    const firstDetail = testCaseDetailFixture(
      'tc_review_signals',
      'test_builder_emits_review_signals',
      'assert first_result',
    )
    const secondDetail = testCaseDetailFixture(
      'tc_command_paths',
      'test_builder_emits_command_paths',
      'assert second_result',
    )
    const firstDetailRequest = new Promise<ReturnType<typeof testCaseDetailFixture>>(resolve => {
      resolveFirstDetail = resolve
    })

    vi.mocked(fetchAssessmentTestCaseDetail)
      .mockImplementationOnce(async () => firstDetailRequest)
      .mockImplementationOnce(async () => secondDetail)

    render(<TestChangesPage />)

    expect(await screen.findByText('Test Cases')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /test_builder_emits_command_paths/ }))

    await waitFor(() => expect(screen.getByText('test_builder_emits_command_paths result summary')).toBeInTheDocument())
    resolveFirstDetail(firstDetail)

    await waitFor(() => expect(fetchAssessmentTestCaseDetail).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByText('test_builder_emits_review_signals result summary')).not.toBeInTheDocument())
    expect(screen.getByText('test_builder_emits_command_paths result summary')).toBeInTheDocument()
  })
})
