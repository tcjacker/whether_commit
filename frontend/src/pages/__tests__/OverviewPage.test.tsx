import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from '../../App'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  window.history.replaceState({}, '', '/')
})

describe('OverviewPage', () => {
  it('uses the edited workspace path for rebuilds and downstream navigation', async () => {
    const fetchMock = vi.spyOn(global, 'fetch').mockImplementation(async (input) => {
      const url = String(input)

      if (url.includes('/api/overview?repo_key=divide_prd_to_ui')) {
        return new Response(JSON.stringify({ detail: 'OVERVIEW_NOT_READY: Please trigger a rebuild first.' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        })
      }

      if (url.endsWith('/api/overview/rebuild')) {
        return new Response(JSON.stringify({ job_id: 'job_123', status: 'pending' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }

      throw new Error(`Unexpected fetch: ${url}`)
    })

    window.history.pushState({}, '', '/?repo_key=divide_prd_to_ui')

    render(<App />)

    const input = await screen.findByLabelText('Workspace Path')
    fireEvent.change(input, { target: { value: '/path/to/repo' } })

    fireEvent.click(screen.getAllByRole('button', { name: '开始重建' })[0])

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/overview/rebuild',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            repo_key: 'divide_prd_to_ui',
            workspace_path: '/path/to/repo',
          }),
        }),
      )
    })

    const reviewLink = screen.getByRole('link', { name: '进入 Change Review' })
    expect(reviewLink).toHaveAttribute(
      'href',
      '/review-graph?repo_key=divide_prd_to_ui&workspace_path=%2FUsers%2Ftc%2Fdivide_prd_to_ui',
    )
  })

  it('shows an explicit no-pending-changes notice for the current workspace', async () => {
    vi.spyOn(global, 'fetch').mockImplementation(async (input) => {
      const url = String(input)

      if (url === '/api/overview?repo_key=divide_prd_to_ui&workspace_path=%2FUsers%2Ftc%2Fdivide_prd_to_ui') {
        return new Response(JSON.stringify({
          repo: { repo_key: 'divide_prd_to_ui', name: 'divide_prd_to_ui', default_branch: 'main' },
          snapshot: {
            base_commit_sha: 'HEAD',
            workspace_snapshot_id: 'ws_clean',
            has_pending_changes: false,
            status: 'ready',
            generated_at: '2026-04-19T00:00:00Z',
          },
          project_summary: {
            what_this_app_seems_to_do: '未检测到待分析的变更',
            technical_narrative: '当前工作区与基线提交一致，无需执行 AI 变更分析。',
            core_flow: 'HEAD -> 干净工作区',
          },
          capability_map: [],
          journeys: [],
          architecture_overview: { nodes: [], edges: [] },
          recent_ai_changes: [],
          change_themes: [],
          agent_harness_status: null,
          agent_harness_metadata: {},
          verification_status: {
            build: { status: 'unknown' },
            unit_tests: { status: 'unknown' },
            integration_tests: { status: 'unknown' },
            scenario_replay: { status: 'unknown' },
            critical_paths: [],
            unverified_areas: [],
            verified_changed_modules: [],
            unverified_changed_modules: [],
            verified_changed_paths: [],
            unverified_changed_paths: [],
            verified_impacts: [],
            unverified_impacts: [],
            affected_tests: [],
            missing_tests_for_changed_paths: [],
            critical_changed_paths: [],
            evidence_by_path: {},
          },
          warnings: ['NO_PENDING_CHANGES'],
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }

      throw new Error(`Unexpected fetch: ${url}`)
    })

    window.history.pushState({}, '', '/?repo_key=divide_prd_to_ui&workspace_path=%2FUsers%2Ftc%2Fdivide_prd_to_ui')

    render(<App />)

    await waitFor(() => expect(screen.getByText('当前 workspace 无待分析变更')).toBeInTheDocument())
    expect(screen.getByText('当前工作区与基线提交一致，Change Review 将显示为空。')).toBeInTheDocument()
  })

  it('renders the change risk summary card when overview data is ready', async () => {
    vi.spyOn(global, 'fetch').mockImplementation(async (input) => {
      const url = String(input)

      if (url === '/api/overview?repo_key=divide_prd_to_ui&workspace_path=%2FUsers%2Ftc%2Fdivide_prd_to_ui') {
        return new Response(JSON.stringify({
          repo: { repo_key: 'divide_prd_to_ui', name: 'divide_prd_to_ui', default_branch: 'main' },
          snapshot: {
            base_commit_sha: 'HEAD',
            workspace_snapshot_id: 'ws_risk',
            has_pending_changes: true,
            status: 'ready',
            generated_at: '2026-04-19T00:00:00Z',
          },
          project_summary: {
            what_this_app_seems_to_do: '正在对后端系统进行技术分析',
            technical_narrative: 'overview ready',
            core_flow: '客户端 -> API 处理器 -> 服务',
          },
          capability_map: [],
          journeys: [],
          architecture_overview: { nodes: [], edges: [] },
          recent_ai_changes: [],
          change_themes: [],
          change_risk_summary: {
            headline: {
              overall_risk_level: 'high',
              overall_risk_summary: '本次改动命中了高风险路径。',
              recommended_focus: ['优先检查订单提交流程'],
            },
            coverage: {
              coverage_status: 'partially_covered',
              affected_test_count: 2,
              verified_changed_path_count: 1,
              unverified_changed_path_count: 1,
              missing_test_paths: ['backend/app/services/orders.py'],
              coverage_summary: '仍有 1 条路径缺少验证。',
            },
            existing_feature_impact: {
              business_impact_summary: '主要影响订单提交能力。',
              affected_capability_count: 1,
              affected_capabilities: [
                {
                  capability_key: 'orders.submit',
                  name: '订单提交',
                  impact_status: 'directly_changed',
                  technical_entrypoints: ['POST /orders'],
                  changed_files: ['backend/app/services/orders.py'],
                  related_modules: ['mod_orders_service'],
                  verification_status: 'partial',
                  impact_basis: [],
                },
              ],
            },
            risk_signals: [],
            agent_metadata: { agent_based_fields: [], rule_based_fields: [] },
          },
          agent_harness_status: null,
          agent_harness_metadata: {},
          verification_status: {
            build: { status: 'unknown' },
            unit_tests: { status: 'unknown' },
            integration_tests: { status: 'unknown' },
            scenario_replay: { status: 'unknown' },
            critical_paths: [],
            unverified_areas: [],
            verified_changed_modules: [],
            unverified_changed_modules: [],
            verified_changed_paths: [],
            unverified_changed_paths: [],
            verified_impacts: [],
            unverified_impacts: [],
            affected_tests: [],
            missing_tests_for_changed_paths: [],
            critical_changed_paths: [],
            evidence_by_path: {},
          },
          warnings: [],
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }

      throw new Error(`Unexpected fetch: ${url}`)
    })

    window.history.pushState({}, '', '/?repo_key=divide_prd_to_ui&workspace_path=%2FUsers%2Ftc%2Fdivide_prd_to_ui')

    render(<App />)

    await waitFor(() => expect(screen.getByText('变更风险总览')).toBeInTheDocument())
    expect(screen.getByText('本次改动命中了高风险路径。')).toBeInTheDocument()
    expect(screen.getByText('订单提交')).toBeInTheDocument()
  })

  it('renders the test asset summary card when overview data is ready', async () => {
    vi.spyOn(global, 'fetch').mockImplementation(async (input) => {
      const url = String(input)

      if (url === '/api/overview?repo_key=divide_prd_to_ui&workspace_path=%2FUsers%2Ftc%2Fdivide_prd_to_ui') {
        return new Response(JSON.stringify({
          repo: { repo_key: 'divide_prd_to_ui', name: 'divide_prd_to_ui', default_branch: 'main' },
          snapshot: {
            base_commit_sha: 'HEAD',
            workspace_snapshot_id: 'ws_test_assets',
            has_pending_changes: true,
            status: 'ready',
            generated_at: '2026-04-24T00:00:00Z',
          },
          project_summary: {
            what_this_app_seems_to_do: '正在对后端系统进行技术分析',
            technical_narrative: 'overview ready',
            core_flow: '客户端 -> API 处理器 -> 服务',
          },
          capability_map: [],
          journeys: [],
          architecture_overview: { nodes: [], edges: [] },
          recent_ai_changes: [
            {
              change_id: 'chg_latest',
              change_title: '工作区差异',
              summary: '新增测试资产摘要。',
              affected_capabilities: ['测试资产健康'],
              technical_entrypoints: ['GET /api/overview'],
              changed_files: [
                'backend/app/schemas/overview.py',
                'frontend/src/types/api.ts',
              ],
              changed_symbols: [],
              changed_routes: ['GET /api/overview'],
              changed_schemas: [],
              changed_jobs: [],
              change_types: ['api_contract_change'],
              directly_changed_modules: [],
              transitively_affected_modules: [],
              affected_entrypoints: ['GET /api/overview'],
              affected_data_objects: [],
              why_impacted: '',
              risk_factors: [],
              review_recommendations: [],
              linked_tests: ['backend/tests/test_overview_inference.py'],
              verification_coverage: 'covered',
              confidence: 'medium',
              change_intent: '',
              coherence: 'focused',
              coherence_groups: [],
            },
          ],
          change_themes: [],
          change_risk_summary: {
            headline: {
              overall_risk_level: 'medium',
              overall_risk_summary: '本次改动需要关注测试覆盖。',
              recommended_focus: [],
            },
            coverage: {
              coverage_status: 'partially_covered',
              affected_test_count: 1,
              verified_changed_path_count: 1,
              unverified_changed_path_count: 1,
              missing_test_paths: ['app/services/orders.py'],
              coverage_summary: '仍有 1 条路径缺少验证。',
            },
            existing_feature_impact: {
              business_impact_summary: '主要影响订单提交能力。',
              affected_capability_count: 1,
              affected_capabilities: [],
            },
            risk_signals: [],
            agent_metadata: { agent_based_fields: [], rule_based_fields: [] },
          },
          test_asset_summary: {
            health_status: 'needs_maintenance',
            total_test_file_count: 1,
            affected_test_count: 1,
            changed_test_file_count: 1,
            stale_or_invalid_test_count: 1,
            duplicate_or_low_value_test_count: 0,
            coverage_gaps: ['app/services/orders.py'],
            recommended_actions: ['更新或淘汰疑似失效的测试资产。'],
            capability_coverage: [
              {
                capability_key: 'orders.submit',
                business_capability: '订单提交',
                coverage_status: 'partial',
                technical_entrypoints: ['POST /orders'],
                covered_paths: ['app/api/orders.py', 'app/services/orders.py'],
                covering_tests: ['tests/test_orders.py::test_submit'],
                gaps: ['app/services/orders.py'],
                maintenance_recommendation: '补齐缺口路径，并确认现有测试仍覆盖真实业务入口。',
              },
            ],
            test_files: [
              {
                path: 'tests/test_orders.py',
                maintenance_status: 'update',
                covered_capabilities: ['订单提交'],
                covered_paths: ['app/api/orders.py', 'app/services/orders.py'],
                linked_entrypoints: ['POST /orders'],
                invalidation_reasons: ['关联业务路径仍有未覆盖或未验证的变更。'],
                recommendation: '更新该测试，使它覆盖当前变更后的真实业务路径。',
                evidence_status: 'test-file-present',
              },
            ],
          },
          agent_harness_status: null,
          agent_harness_metadata: {},
          verification_status: {
            build: { status: 'unknown' },
            unit_tests: { status: 'unknown' },
            integration_tests: { status: 'unknown' },
            scenario_replay: { status: 'unknown' },
            critical_paths: [],
            unverified_areas: [],
            verified_changed_modules: [],
            unverified_changed_modules: [],
            verified_changed_paths: [],
            unverified_changed_paths: [],
            verified_impacts: [],
            unverified_impacts: [],
            affected_tests: [],
            missing_tests_for_changed_paths: [],
            critical_changed_paths: [],
            evidence_by_path: {},
          },
          warnings: [],
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }

      throw new Error(`Unexpected fetch: ${url}`)
    })

    window.history.pushState({}, '', '/?repo_key=divide_prd_to_ui&workspace_path=%2FUsers%2Ftc%2Fdivide_prd_to_ui')

    render(<App />)

    await waitFor(() => expect(screen.getByText('测试资产健康')).toBeInTheDocument())
    expect(screen.getByText('项目结构变更')).toBeInTheDocument()
    expect(screen.getByText('backend/')).toBeInTheDocument()
    expect(screen.getByText('app/schemas/overview.py')).toBeInTheDocument()
    expect(screen.getByText('这段 diff 的意义')).toBeInTheDocument()
    expect(screen.getByText('tests/test_orders.py')).toBeInTheDocument()
    expect(screen.getByText('更新或淘汰疑似失效的测试资产。')).toBeInTheDocument()
  })
})
