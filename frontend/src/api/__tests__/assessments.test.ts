import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  fetchAssessmentTestCaseDetail,
  fetchAssessmentTests,
  triggerFileAgentAssessment,
} from '../assessments'
import type { TestCaseDetail, TestManagementSummary } from '../../types/api'

describe('assessment api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts codex assessment requests in Chinese by default', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await triggerFileAgentAssessment('demo', 'aca_ws_1', 'cf_abc123', '/tmp/demo')

    const url = String(fetchSpy.mock.calls[0][0])
    expect(url).toContain('/api/assessments/aca_ws_1/files/cf_abc123/agent-assessment?')
    expect(url).toContain('repo_key=demo')
    expect(url).toContain('workspace_path=%2Ftmp%2Fdemo')
    expect(url).toContain('language=zh-CN')
  })

  it('fetches test management summaries for an assessment', async () => {
    const summary: TestManagementSummary = {
      assessment_id: 'aca_ws',
      repo_key: 'demo',
      changed_test_file_count: 1,
      test_case_count: 1,
      evidence_grade_counts: { direct: 1 },
      command_status_counts: { passed: 1 },
      files: [
        {
          file_id: 'tf_1',
          path: 'tests/test_demo.py',
          status: 'added',
          additions: 12,
          deletions: 0,
          test_case_count: 1,
          strongest_evidence_grade: 'direct',
          weakest_evidence_grade: 'direct',
          latest_command_status: 'passed',
          test_cases: [
            {
              test_case_id: 'tc_1',
              file_id: 'tf_1',
              path: 'tests/test_demo.py',
              name: 'test_demo',
              status: 'added',
              extraction_confidence: 'certain',
              evidence_grade: 'direct',
              weakest_evidence_grade: 'direct',
              last_status: 'passed',
              covered_changes_preview: [
                {
                  hunk_id: 'hunk_1',
                  path: 'src/demo.py',
                  evidence_grade: 'direct',
                  risk_level: 'low',
                },
              ],
              highest_risk_covered_hunk_id: 'hunk_1',
              intent_summary: {
                text: 'covers demo behavior',
                source: 'rule_derived',
                basis: ['test name'],
              },
            },
          ],
        },
      ],
      unknowns: [],
    }
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(summary), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await fetchAssessmentTests('demo', 'aca_ws', '/tmp/backend-visiable')

    expect(String(fetchSpy.mock.calls[0][0])).toBe(
      '/api/assessments/aca_ws/tests?repo_key=demo&workspace_path=%2Ftmp%2Fbackend-visiable',
    )
    expect(result).toEqual(summary)
  })

  it('fetches test case details for an assessment', async () => {
    const detail: TestCaseDetail = {
      test_case: {
        test_case_id: 'tc_1',
        file_id: 'tf_1',
        path: 'tests/test_demo.py',
        name: 'test_demo',
        status: 'modified',
        extraction_confidence: 'heuristic',
        evidence_grade: 'indirect',
        weakest_evidence_grade: 'indirect',
        last_status: 'not_run',
        covered_changes_preview: [],
        highest_risk_covered_hunk_id: 'hunk_1',
        intent_summary: {
          text: 'verifies demo output',
          source: 'agent_claim',
          basis: ['agent claim'],
        },
      },
      diff_hunks: [],
      full_body: [],
      assertions: [],
      covered_scenarios: [
        {
          title: 'Scenario named by test: test demo.',
          source: 'rule_derived',
          basis: ['test_name'],
        },
      ],
      covered_changes: [
        {
          path: 'src/demo.py',
          symbol: 'demo',
          hunk_id: 'hunk_1',
          relationship: 'imports',
          evidence_grade: 'indirect',
          basis: ['imports changed module'],
        },
      ],
      recommended_commands: [
        {
          command_id: 'cmd_1',
          command: 'pytest tests/test_demo.py::test_demo',
          reason: 'Run the focused test case.',
          scope: 'test_case',
          status: 'not_run',
          last_run_id: null,
        },
      ],
      related_agent_claims: [],
      unknowns: [],
    }
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(detail), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await fetchAssessmentTestCaseDetail('demo', 'aca_ws', 'tc_1', '/repo')

    expect(String(fetchSpy.mock.calls[0][0])).toBe(
      '/api/assessments/aca_ws/tests/tc_1?repo_key=demo&workspace_path=%2Frepo',
    )
    expect(result).toEqual(detail)
  })
})
