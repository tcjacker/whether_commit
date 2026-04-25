import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ProjectSummary, CapabilityItem, ChangeRiskSummary, TestAssetSummary } from '../../../types/api'
import { ProjectSummaryCard } from '../ProjectSummaryCard'
import { CapabilityMapCard } from '../CapabilityMapCard'
import { ChangeRiskSummaryCard } from '../ChangeRiskSummaryCard'
import { TestAssetSummaryCard } from '../TestAssetSummaryCard'
import { ProjectStructureChangeCard } from '../ProjectStructureChangeCard'

type SummaryFixture = ProjectSummary & {
  overall_assessment?: string
  impact_level?: 'high' | 'medium' | 'low' | 'unknown'
  impact_basis?: Array<string | Record<string, unknown>>
  affected_capability_count?: number
  affected_entrypoints?: string[]
  critical_paths?: string[]
  verification_gaps?: string[]
  priority_themes?: string[]
  degraded_hint?: string
}

type CapabilityFixture = CapabilityItem & {
  impact_status?: string
  impact_reason?: string
  related_themes?: string[]
  verification_status?: string
}

afterEach(() => {
  cleanup()
})

describe('overview cards', () => {
  it('renders project structure changes as a directory tree with file-level diff meaning', async () => {
    const riskSummary: ChangeRiskSummary = {
      headline: {
        overall_risk_level: 'medium',
        overall_risk_summary: 'Overview 输出和首页展示发生变化。',
        recommended_focus: ['backend/app/schemas/overview.py'],
      },
      coverage: {
        coverage_status: 'partially_covered',
        affected_test_count: 2,
        verified_changed_path_count: 1,
        unverified_changed_path_count: 1,
        missing_test_paths: ['backend/app/services/test_asset_summary.py'],
        coverage_summary: '仍有内部规则路径需要验证。',
      },
      existing_feature_impact: {
        business_impact_summary: '主要影响测试资产健康展示。',
        affected_capability_count: 1,
        affected_capabilities: [
          {
            capability_key: 'test.assets',
            name: '测试资产健康',
            impact_status: 'directly_changed',
            technical_entrypoints: ['GET /api/overview'],
            changed_files: ['backend/app/schemas/overview.py', 'frontend/src/types/api.ts'],
            related_modules: ['mod_overview'],
            verification_status: 'partial',
            impact_basis: [],
          },
        ],
      },
      risk_signals: [
        {
          signal_key: 'contract_changed',
          title: '响应结构扩展',
          severity: 'medium',
          reason: 'overview API 新增测试资产字段。',
          related_files: ['backend/app/schemas/overview.py'],
          related_modules: [],
          mitigation: '确认前端兼容旧 snapshot。',
        },
      ],
      agent_metadata: { agent_based_fields: [], rule_based_fields: [] },
    }
    const testSummary: TestAssetSummary = {
      health_status: 'needs_maintenance',
      total_test_file_count: 1,
      affected_test_count: 1,
      changed_test_file_count: 1,
      stale_or_invalid_test_count: 1,
      duplicate_or_low_value_test_count: 0,
      coverage_gaps: ['backend/app/services/test_asset_summary.py'],
      recommended_actions: ['补齐内部规则路径测试。'],
      capability_coverage: [],
      test_files: [
        {
          path: 'backend/tests/test_overview_inference.py',
          maintenance_status: 'update',
          covered_capabilities: ['测试资产健康'],
          covered_paths: ['backend/app/schemas/overview.py'],
          linked_entrypoints: ['GET /api/overview'],
          invalidation_reasons: [],
          recommendation: '更新该测试，使它覆盖当前变更后的真实业务路径。',
          evidence_status: 'test-file-present',
        },
      ],
    }

    render(
      <ProjectStructureChangeCard
        changes={[
          {
            change_id: 'chg_latest',
            change_title: '工作区差异',
            summary: '新增测试资产摘要。',
            affected_capabilities: ['测试资产健康'],
            technical_entrypoints: ['GET /api/overview'],
            changed_files: [
              'backend/app/schemas/overview.py',
              'backend/app/services/overview_inference/test_asset_summary.py',
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
        ]}
        fileReviewSummaries={[
          {
            path: 'backend/app/schemas/overview.py',
            file_role: 'API schema',
            risk_level: 'medium',
            diff_summary: '+64 lines · additive contract',
            diff_snippets: [
              { type: 'add', line: '+121', text: 'class TestAssetSummary(BaseModel):' },
              { type: 'add', line: '+216', text: 'test_asset_summary: TestAssetSummary = TestAssetSummary()' },
            ],
            product_meaning: '后端生成：这个文件把测试资产管理正式变成 overview API 契约的一部分。',
            intent_evidence: ['codex: 用户要求把测试资产管理接入 overview 首页'],
            review_focus: ['确认旧 snapshot 兼容'],
            related_entrypoints: ['GET /api/overview'],
            related_capabilities: ['测试资产健康'],
            related_tests: ['backend/tests/test_overview_inference.py'],
            evidence_basis: ['+64 lines · additive contract'],
            generated_by: 'rules',
          },
          {
            path: 'backend/app/services/overview_inference/test_asset_summary.py',
            file_role: 'Internal rule/service',
            risk_level: 'high',
            diff_summary: 'new file · rule engine',
            diff_snippets: [
              { type: 'add', line: '+8', text: 'class TestAssetSummaryBuilder:' },
            ],
            product_meaning: '后端生成：它把测试文件是否还值得保留从主观判断变成可解释的规则事实。',
            review_focus: ['确认规则事实是否保守'],
            related_entrypoints: ['GET /api/overview'],
            related_capabilities: ['测试资产健康'],
            related_tests: ['backend/tests/test_overview_inference.py'],
            evidence_basis: ['unverified_changed_path'],
            generated_by: 'rules',
          },
        ]}
        changeRiskSummary={riskSummary}
        testAssetSummary={testSummary}
        loading={false}
      />,
    )

    expect(screen.getByText('项目结构变更')).toBeInTheDocument()
    expect(screen.getByText('backend/')).toBeInTheDocument()
    expect(screen.getByText('app/schemas/overview.py')).toBeInTheDocument()
    expect(screen.getByText('frontend/')).toBeInTheDocument()
    expect(screen.getByText('这段 diff 的意义')).toBeInTheDocument()
    expect(screen.getByText('diff 摘要 · backend/app/schemas/overview.py')).toBeInTheDocument()
    expect(screen.getByLabelText('文件 diff 滚动窗口')).toBeInTheDocument()
    expect(screen.queryByText('文件与入口')).not.toBeInTheDocument()
    expect(screen.queryByText('解释层')).not.toBeInTheDocument()
    expect(screen.queryByText('规则识别到的业务能力')).not.toBeInTheDocument()
    expect(screen.queryByText('规则识别到的技术入口')).not.toBeInTheDocument()
    expect(screen.getAllByText('后端生成：这个文件把测试资产管理正式变成 overview API 契约的一部分。').length).toBeGreaterThan(0)
    expect(screen.getByText('依据：codex: 用户要求把测试资产管理接入 overview 首页')).toBeInTheDocument()
    expect(screen.queryByText('确认旧 snapshot 兼容')).not.toBeInTheDocument()
    expect(screen.queryByText('测试资产健康')).not.toBeInTheDocument()
    expect(screen.getAllByText('GET /api/overview').length).toBeGreaterThan(0)
    expect(screen.getAllByText('backend/tests/test_overview_inference.py').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByText('app/services/overview_inference/test_asset_summary.py'))

    await waitFor(() => expect(screen.getByText('diff 摘要 · backend/app/services/overview_inference/test_asset_summary.py')).toBeInTheDocument())
    expect(screen.getAllByText('后端生成：它把测试文件是否还值得保留从主观判断变成可解释的规则事实。').length).toBeGreaterThan(0)
    expect(screen.queryByText('后端生成：这个文件把测试资产管理正式变成 overview API 契约的一部分。')).not.toBeInTheDocument()
  })

  it('renders test asset health with coverage paths and stale test guidance', () => {
    const summary: TestAssetSummary = {
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
    }

    render(<TestAssetSummaryCard summary={summary} loading={false} />)

    expect(screen.getByText('测试资产健康')).toBeInTheDocument()
    expect(screen.getByText('订单提交')).toBeInTheDocument()
    expect(screen.getByText('POST /orders')).toBeInTheDocument()
    expect(screen.getByText('tests/test_orders.py')).toBeInTheDocument()
    expect(screen.getAllByText(/app\/services\/orders\.py/).length).toBeGreaterThan(0)
    expect(screen.getByText('更新或淘汰疑似失效的测试资产。')).toBeInTheDocument()
  })

  it('renders the top change risk summary card from overview data', () => {
    const summary: ChangeRiskSummary = {
      headline: {
        overall_risk_level: 'high',
        overall_risk_summary: '本次改动命中了高风险路径。',
        recommended_focus: ['优先补充订单提交流程测试'],
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
    }

    render(<ChangeRiskSummaryCard summary={summary} loading={false} />)

    expect(screen.getByText('变更风险总览')).toBeInTheDocument()
    expect(screen.getByText('本次改动命中了高风险路径。')).toBeInTheDocument()
    expect(screen.getByText('订单提交')).toBeInTheDocument()
  })

  it('renders accepted summary and capability metadata', () => {
    const summary: SummaryFixture = {
      what_this_app_seems_to_do: '旧摘要',
      technical_narrative: '旧叙述',
      core_flow: '订单从创建到支付',
      overall_assessment: '本次未提交修改直接影响订单创建链路，需要优先关注。',
      impact_level: 'high',
      impact_basis: [
        {
          target_id: 'POST /orders',
          reason: '订单创建入口被修改',
          evidence: ['app/api/orders.py'],
        },
      ],
      affected_capability_count: 3,
      affected_entrypoints: ['POST /orders'],
      critical_paths: ['创建订单 -> 校验 -> 入库'],
      verification_gaps: ['缺少回归测试覆盖'],
      priority_themes: ['订单提交流程', '校验逻辑'],
    }

    const capabilities: CapabilityFixture[] = [
      {
        capability_key: 'orders.create',
        name: '创建订单',
        status: 'recently_changed',
        linked_modules: ['app/api/orders.py'],
        linked_routes: ['POST /orders'],
        impact_status: 'directly_changed',
        impact_reason: '变更直接落在下单入口。',
        related_themes: ['订单提交流程'],
        verification_status: 'partial',
      },
    ]

    render(
      <div>
        <ProjectSummaryCard summary={summary} loading={false} />
        <CapabilityMapCard
          capabilities={capabilities}
          loading={false}
          highlightedKeys={new Set()}
          selectedKey={null}
          onSelect={() => {}}
        />
      </div>,
    )

    expect(screen.getByText('本次未提交修改直接影响订单创建链路，需要优先关注。')).toBeInTheDocument()
    expect(screen.getByText('高')).toBeInTheDocument()
    expect(screen.getByText('POST /orders · 订单创建入口被修改')).toBeInTheDocument()
    expect(screen.getByText('1 条证据')).toBeInTheDocument()
    expect(screen.getAllByText('订单提交流程')).toHaveLength(2)
    expect(screen.getByText('缺少回归测试覆盖')).toBeInTheDocument()

    expect(screen.getByText('创建订单')).toBeInTheDocument()
    expect(screen.getByText('直接变更')).toBeInTheDocument()
    expect(screen.getByText('部分覆盖')).toBeInTheDocument()
    expect(screen.getByText('变更直接落在下单入口。')).toBeInTheDocument()
    expect(screen.getByText('关联入口')).toBeInTheDocument()
  })

  it('renders degraded hint when harness falls back', () => {
    const summary: SummaryFixture = {
      what_this_app_seems_to_do: '源代码静态分析摘要',
      technical_narrative: '静态叙述',
      core_flow: '核心流程',
      overall_assessment: 'Agent harness unavailable; showing source-derived overview summary.',
      impact_level: 'unknown',
      impact_basis: [],
      affected_capability_count: 0,
      affected_entrypoints: [],
      critical_paths: [],
      verification_gaps: [],
      priority_themes: [],
    }

    render(<ProjectSummaryCard summary={summary} loading={false} />)

    expect(screen.getByText('未知')).toBeInTheDocument()
    expect(screen.getByText('降级提示')).toBeInTheDocument()
    expect(screen.getByText('当前结论来自源代码静态分析，Agent 判定未能稳定接入。')).toBeInTheDocument()
    expect(screen.getByText('Agent harness unavailable; showing source-derived overview summary.')).toBeInTheDocument()
  })

  it('falls back to legacy capability fields when new metadata is absent', () => {
    const capabilities: CapabilityFixture[] = [
      {
        capability_key: 'legacy.orders',
        name: '旧能力',
        status: 'recently_changed',
        linked_modules: ['legacy/orders.ts'],
        linked_routes: ['/legacy/orders'],
      },
    ]

    render(
      <CapabilityMapCard
        capabilities={capabilities}
        loading={false}
        highlightedKeys={new Set()}
        selectedKey={null}
        onSelect={() => {}}
      />,
    )

    expect(screen.getByText('旧能力')).toBeInTheDocument()
    expect(screen.getByText('最近变更')).toBeInTheDocument()
    expect(screen.getByText('关联入口')).toBeInTheDocument()
    expect(screen.getByText('/legacy/orders')).toBeInTheDocument()
  })
})
