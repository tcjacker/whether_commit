import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TestCaseCodePanel } from '../TestCaseCodePanel'
import { TestCaseList } from '../TestCaseList'
import { TestEvidencePanel } from '../TestEvidencePanel'
import { TestResultPanel } from '../TestResultPanel'
import type { TestCaseDetail, TestManagementSummary } from '../../../types/api'

const summary: TestManagementSummary = {
  assessment_id: 'aca_ws_1',
  repo_key: 'demo',
  changed_test_file_count: 1,
  test_case_count: 1,
  evidence_grade_counts: { direct: 1 },
  command_status_counts: { not_run: 1 },
  files: [
    {
      file_id: 'tf_auth',
      path: 'frontend/src/auth/__tests__/login-flow.test.tsx',
      status: 'modified',
      additions: 18,
      deletions: 3,
      test_case_count: 1,
      strongest_evidence_grade: 'direct',
      weakest_evidence_grade: 'direct',
      latest_command_status: 'not_run',
      test_cases: [
        {
          test_case_id: 'tc_login_redirect',
          file_id: 'tf_auth',
          path: 'frontend/src/auth/__tests__/login-flow.test.tsx',
          name: 'redirects to saved workspace after login',
          status: 'modified',
          extraction_confidence: 'certain',
          evidence_grade: 'direct',
          weakest_evidence_grade: 'direct',
          last_status: 'not_run',
          covered_changes_preview: [
            {
              path: 'frontend/src/auth/login.ts',
              hunk_id: 'hunk_login_redirect',
              risk_level: 'medium',
              evidence_grade: 'direct',
            },
          ],
          highest_risk_covered_hunk_id: 'hunk_login_redirect',
          intent_summary: {
            text: 'Ensures login keeps the workspace redirect target.',
            source: 'rule_derived',
            basis: ['test name mentions redirect', 'assertion checks workspace path'],
          },
        },
      ],
    },
  ],
  unknowns: [],
}

function detailFixture(): TestCaseDetail {
  return {
    test_case: summary.files[0].test_cases[0],
    diff_hunks: [
      {
        hunk_id: 'test_hunk_1',
        old_start: 12,
        old_lines: 2,
        new_start: 12,
        new_lines: 4,
        hunk_fingerprint: 'sha256:test-hunk',
        lines: [
          { type: 'context', content: 'render(<LoginForm />)' },
          { type: 'add', content: "expect(navigate).toHaveBeenCalledWith('/workspaces/ws_1')" },
        ],
      },
    ],
    full_body: [
      { type: 'context', content: "it('redirects to saved workspace after login', async () => {" },
      { type: 'context', content: "expect(navigate).toHaveBeenCalledWith('/workspaces/ws_1')" },
      { type: 'context', content: '})' },
    ],
    assertions: [
      { type: 'add', content: "expect(navigate).toHaveBeenCalledWith('/workspaces/ws_1')" },
    ],
    covered_scenarios: [
      {
        title: 'Scenario named by test: redirects to saved workspace after login.',
        source: 'rule_derived',
        basis: ['test_name'],
      },
      {
        title: "Assertion checks: expect(navigate).toHaveBeenCalledWith('/workspaces/ws_1')",
        source: 'rule_derived',
        basis: ['assertion'],
      },
    ],
    covered_changes: [
      {
        path: 'frontend/src/auth/login.ts',
        symbol: 'redirectAfterLogin',
        hunk_id: 'hunk_login_redirect',
        relationship: 'names_changed_symbol',
        evidence_grade: 'direct',
        basis: ['test name matches changed symbol', 'assertion covers redirect path'],
      },
    ],
    recommended_commands: [
      {
        command_id: 'cmd_login',
        command: 'npm test -- login-flow.test.tsx',
        reason: 'Run the changed login redirect test.',
        scope: 'test_case',
        status: 'not_run',
        last_run_id: null,
      },
    ],
    related_agent_claims: [
      {
        claim_id: 'claim_login_redirect',
        type: 'feature',
        text: 'Login now preserves the workspace redirect target.',
        source: 'codex_agent',
        session_id: 'sess_login',
        message_ref: 'msg_login',
        tool_call_ref: 'call_login',
        related_files: ['frontend/src/auth/login.ts'],
        confidence: 'high',
      },
    ],
    unknowns: [
      'browser redirect side effect not executed in this assessment',
      'server session expiry path not exercised',
    ],
  }
}

function deletedDetailFixture(): TestCaseDetail {
  const base = detailFixture()
  return {
    ...base,
    test_case: {
      ...base.test_case,
      test_case_id: 'tc_deleted',
      name: 'removes legacy login fallback',
      status: 'deleted',
      extraction_confidence: 'fallback',
      evidence_grade: 'unknown',
      weakest_evidence_grade: 'unknown',
      last_status: 'unknown',
      highest_risk_covered_hunk_id: null,
      intent_summary: {
        text: 'Deleted test case could not be mapped to current changed code.',
        source: 'unknown',
        basis: ['deletion unknown'],
      },
    },
    covered_changes: [],
    covered_scenarios: [],
    recommended_commands: [],
    unknowns: ['deletion unknown', 'legacy fallback coverage unknown'],
  }
}

describe('test workbench panels', () => {
  afterEach(() => cleanup())

  it('TestCaseList renders test file path, case name, evidence grade, and extraction confidence', () => {
    const onSelect = vi.fn()

    render(
      <TestCaseList
        summary={summary}
        selectedTestCaseId="tc_login_redirect"
        onSelect={onSelect}
      />,
    )

    const panel = screen.getByRole('complementary', { name: 'test-cases' })
    expect(within(panel).getByText('Test Cases')).toBeInTheDocument()
    expect(within(panel).getByText('frontend/src/auth/__tests__/login-flow.test.tsx')).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: /redirects to saved workspace after login/ })).toBeInTheDocument()
    expect(within(panel).getByText('direct')).toBeInTheDocument()
    expect(within(panel).getByText('certain')).toBeInTheDocument()
    expect(within(panel).getByText('hunk_login_redirect')).toBeInTheDocument()

    fireEvent.click(within(panel).getByRole('button', { name: /redirects to saved workspace after login/ }))
    expect(onSelect).toHaveBeenCalledWith(summary.files[0].test_cases[0])
  })

  it('TestCaseCodePanel renders selected test case name and assertion/code line', () => {
    render(<TestCaseCodePanel detail={detailFixture()} />)

    const panel = screen.getByRole('main', { name: 'test-code' })
    expect(within(panel).getByText('redirects to saved workspace after login')).toBeInTheDocument()
    expect(within(panel).getByText("+expect(navigate).toHaveBeenCalledWith('/workspaces/ws_1')")).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Diff' })).toHaveAttribute('aria-pressed', 'true')

    const assertionsButton = within(panel).getByRole('button', { name: 'Assertions only' })
    fireEvent.click(assertionsButton)
    expect(assertionsButton).toHaveAttribute('aria-pressed', 'true')
    expect(within(panel).getByRole('button', { name: 'Diff' })).toHaveAttribute('aria-pressed', 'false')
    expect(within(panel).getByText("+expect(navigate).toHaveBeenCalledWith('/workspaces/ws_1')")).toBeInTheDocument()
  })

  it('TestEvidencePanel renders intent, covered changed code, agent claims, and recommended command', () => {
    render(<TestEvidencePanel detail={detailFixture()} />)

    const panel = screen.getByRole('complementary', { name: 'test-evidence' })
    expect(within(panel).getByText('Ensures login keeps the workspace redirect target.')).toBeInTheDocument()
    expect(within(panel).getByText('rule derived')).toBeInTheDocument()
    expect(within(panel).getByText('Covered Scenarios')).toBeInTheDocument()
    expect(within(panel).getByText('Scenario named by test: redirects to saved workspace after login.')).toBeInTheDocument()
    expect(within(panel).getByText("Assertion checks: expect(navigate).toHaveBeenCalledWith('/workspaces/ws_1')")).toBeInTheDocument()
    expect(within(panel).getByText('frontend/src/auth/login.ts')).toBeInTheDocument()
    expect(within(panel).getByText('redirectAfterLogin')).toBeInTheDocument()
    expect(within(panel).getByText('names changed symbol')).toBeInTheDocument()
    expect(within(panel).getByText('Login now preserves the workspace redirect target.')).toBeInTheDocument()
    expect(within(panel).getByText(/feature · codex_agent · high/)).toBeInTheDocument()
    expect(within(panel).getByText('npm test -- login-flow.test.tsx')).toBeInTheDocument()
  })

  it('deleted test case renders status deleted, extraction confidence fallback, and deletion unknown', () => {
    render(<TestEvidencePanel detail={deletedDetailFixture()} />)

    const panel = screen.getByRole('complementary', { name: 'test-evidence' })
    expect(within(panel).getByText('deleted')).toBeInTheDocument()
    expect(within(panel).getByText('fallback')).toBeInTheDocument()
    expect(within(panel).getAllByText('unknown').length).toBeGreaterThan(0)
    const unknowns = within(panel).getByRole('heading', { name: 'Unknowns' }).closest('section')
    expect(unknowns).not.toBeNull()
    expect(within(unknowns as HTMLElement).getByText('deletion unknown')).toBeInTheDocument()
    expect(within(unknowns as HTMLElement).getByText('legacy fallback coverage unknown')).toBeInTheDocument()
    expect(within(unknowns as HTMLElement).queryByText('No unknowns recorded.')).not.toBeInTheDocument()
  })

  it('TestResultPanel confirms rerun before executing and then loads Agent analysis', async () => {
    const runResult = {
      run_id: 'run_login_1',
      source: 'rerun' as const,
      command_id: 'cmd_login',
      command: 'npm test -- login-flow.test.tsx',
      status: 'passed' as const,
      exit_code: 0,
      duration_ms: 128,
      stdout: '1 passed',
      stderr: '',
      stdout_truncated: false,
      stderr_truncated: false,
      timed_out: false,
      started_at: '2026-04-26T00:00:00Z',
      finished_at: '2026-04-26T00:00:01Z',
      captured_at: '2026-04-26T00:00:01Z',
      argv: ['npm', 'test', '--', 'login-flow.test.tsx'],
      executed_cases: [
        {
          node_id: 'frontend/src/auth/__tests__/login-flow.test.tsx::redirects to saved workspace after login',
          name: 'redirects to saved workspace after login',
          status: 'passed' as const,
          source: 'collect_only' as const,
          scenarios: [],
          test_data: ["'/workspaces/ws_1'"],
        },
      ],
      analysis: {
        summary: 'Runner captured one passing login redirect test.',
        scenarios: [],
        test_data: [],
        coverage_gaps: [],
        source: 'rule_derived' as const,
        basis: ['runner_output'],
      },
      evidence_grade: 'direct' as const,
    }
    const agentAnalysis = {
      summary: 'Agent analysis: validates saved workspace redirect with workspace ws_1 test data.',
      scenarios: [
        {
          title: 'Successful login redirects to the saved workspace path.',
          source: 'generated' as const,
          basis: ['executed_case', 'test_data'],
        },
      ],
      test_data: ["'/workspaces/ws_1'"],
      covered_code_analysis: [
        {
          path: 'frontend/src/auth/login.ts',
          symbol: 'redirectAfterLogin',
          hunk_id: 'hunk_login_redirect',
          relationship: 'calls' as const,
          evidence_grade: 'direct' as const,
          analysis: 'The assertion checks the changed redirect target returned by redirectAfterLogin.',
          basis: ['assertion', 'covered_change'],
        },
      ],
      coverage_gaps: ['Does not cover expired session redirect handling.'],
      source: 'generated' as const,
      basis: ['run_login_1', 'test_file_parse'],
    }
    const onRunCommand = vi.fn().mockResolvedValue(runResult)
    let resolveAgentAnalysis: (analysis: typeof agentAnalysis) => void = () => {}
    const agentAnalysisPromise = new Promise<typeof agentAnalysis>(resolve => {
      resolveAgentAnalysis = resolve
    })
    const onAnalyzeResult = vi.fn().mockReturnValue(agentAnalysisPromise)

    render(
      <TestResultPanel
        detail={detailFixture()}
        onRunCommand={onRunCommand}
        onAnalyzeResult={onAnalyzeResult}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'ReRun' }))

    expect(onRunCommand).not.toHaveBeenCalled()
    const modal = screen.getByRole('dialog', { name: 'Confirm test rerun' })
    expect(within(modal).getByText('npm test -- login-flow.test.tsx')).toBeInTheDocument()
    expect(within(modal).getByText('Run the changed login redirect test.')).toBeInTheDocument()

    fireEvent.click(within(modal).getByRole('button', { name: 'Run Test' }))

    await waitFor(() => expect(onRunCommand).toHaveBeenCalledTimes(1))
    expect(onRunCommand).toHaveBeenCalledWith(detailFixture().recommended_commands[0])
    await waitFor(() => expect(onAnalyzeResult).toHaveBeenCalledWith('run_login_1'))
    expect(within(modal).getByText('Analyzing executed cases, test data, and covered scenarios...')).toBeInTheDocument()
    expect(within(modal).queryByText(runResult.analysis.summary)).not.toBeInTheDocument()

    await act(async () => {
      resolveAgentAnalysis(agentAnalysis)
      await agentAnalysisPromise
    })

    expect(await within(modal).findByText(agentAnalysis.summary)).toBeInTheDocument()
    expect(within(modal).getByRole('heading', { name: 'Covered Scenarios' })).toBeInTheDocument()
    expect(within(modal).getByRole('heading', { name: 'Covered Changed Code' })).toBeInTheDocument()
    expect(within(modal).getByText('frontend/src/auth/login.ts')).toBeInTheDocument()
    expect(within(modal).getByText('calls · direct · hunk_login_redirect')).toBeInTheDocument()
    expect(within(modal).getByText('The assertion checks the changed redirect target returned by redirectAfterLogin.')).toBeInTheDocument()
    expect(within(modal).getByRole('heading', { name: 'Test Data' })).toBeInTheDocument()
    expect(within(modal).getByRole('heading', { name: 'Coverage Gaps' })).toBeInTheDocument()
    expect(within(modal).getByRole('heading', { name: 'Evidence Basis' })).toBeInTheDocument()
    expect(within(modal).getByText('Successful login redirects to the saved workspace path.')).toBeInTheDocument()
    expect(within(modal).getByText('redirects to saved workspace after login')).toBeInTheDocument()
    expect(within(modal).getByText('Status: passed')).toBeInTheDocument()
    expect(within(modal).getByText('Status evidence: inferred from command exit 0')).toBeInTheDocument()
    expect(within(modal).getByText('Case name source: collect-only discovery')).toBeInTheDocument()
  })

  it('TestResultPanel auto-closes Agent Analyze progress modal after successful analysis', async () => {
    const storedDetail: TestCaseDetail = {
      ...detailFixture(),
      test_results: [
        {
          run_id: 'run_stored_1',
          source: 'rerun',
          command: 'npm test -- login-flow.test.tsx',
          status: 'passed',
          exit_code: 0,
          duration_ms: 128,
          stdout: '1 passed',
          stderr: '',
          executed_cases: [],
          analysis: {
            summary: 'Stored rule analysis.',
            scenarios: [],
            test_data: [],
            coverage_gaps: [],
            source: 'rule_derived',
            basis: ['runner_output'],
          },
          captured_at: '2026-04-26T00:00:01Z',
          evidence_grade: 'direct',
        },
      ],
    }
    const agentAnalysis = {
      summary: 'Agent analysis completed.',
      scenarios: [],
      test_data: [],
      covered_code_analysis: [],
      coverage_gaps: [],
      source: 'generated' as const,
      basis: ['codex_agent'],
    }
    let resolveAgentAnalysis: (analysis: typeof agentAnalysis) => void = () => {}
    const agentAnalysisPromise = new Promise<typeof agentAnalysis>(resolve => {
      resolveAgentAnalysis = resolve
    })
    const onAnalyzeResult = vi.fn().mockReturnValue(agentAnalysisPromise)

    render(<TestResultPanel detail={storedDetail} onAnalyzeResult={onAnalyzeResult} />)

    fireEvent.click(screen.getByRole('button', { name: 'Agent Analyze' }))

    expect(screen.getByRole('dialog', { name: 'Agent test result analysis' })).toBeInTheDocument()
    expect(screen.getByText('Analyzing stored test result, executed cases, and test code...')).toBeInTheDocument()

    await act(async () => {
      resolveAgentAnalysis(agentAnalysis)
      await agentAnalysisPromise
    })

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Agent test result analysis' })).not.toBeInTheDocument()
    })
    expect(screen.getByText('Agent analysis refreshed just now.')).toBeInTheDocument()
    expect(onAnalyzeResult).toHaveBeenCalledWith('run_stored_1')
  })
})
