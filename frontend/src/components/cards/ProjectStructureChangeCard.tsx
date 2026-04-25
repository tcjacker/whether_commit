import { useState } from 'react'
import type { ChangeRiskSummary, FileReviewSummary, RecentAIChange, TestAssetSummary } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { EmptyState } from '../shared/EmptyState'
import { StatusBadge } from '../shared/StatusBadge'
import styles from './ProjectStructureChangeCard.module.css'

interface Props {
  changes: RecentAIChange[]
  fileReviewSummaries: FileReviewSummary[]
  changeRiskSummary: ChangeRiskSummary | null
  testAssetSummary: TestAssetSummary | null
  loading: boolean
}

interface FileNode {
  path: string
  displayPath: string
  root: string
  kind: 'api' | 'internal' | 'test' | 'frontend' | 'docs' | 'config'
  risk: 'high' | 'medium' | 'low'
}

interface FileDetail {
  lead: string
  statusLabel: string
  entrypoints: Array<{ label: string; value: string }>
  tags: string[]
  coreMeaning: string
  diffTitle: string
  diffBadge: string
  diffLines: Array<{ type: 'add' | 'delete' | 'context'; line: string; text: string }>
  meaningTitle: string
  meaningBullets: Array<{ tone: 'good' | 'warn' | 'risk'; text: string }>
  flow: Array<{ title: string; caption: string }>
}

const KIND_LABELS: Record<FileNode['kind'], string> = {
  api: '对外接口',
  internal: '内部模块',
  test: '测试资产',
  frontend: '首页展示',
  docs: '文档',
  config: '配置',
}

function fileKind(path: string): FileNode['kind'] {
  const lower = path.toLowerCase()
  if (lower.includes('/test') || lower.includes('test_') || lower.includes('.test.')) return 'test'
  if (lower.startsWith('frontend/') || lower.includes('/components/') || lower.includes('/pages/')) return 'frontend'
  if (lower.startsWith('docs/') || lower.endsWith('.md')) return 'docs'
  if (lower.includes('/api/') || lower.includes('/schemas/') || lower.endsWith('api.ts')) return 'api'
  if (lower.includes('config') || lower.includes('package.json') || lower.endsWith('.yml') || lower.endsWith('.yaml')) return 'config'
  return 'internal'
}

function fileRisk(path: string, summary: ChangeRiskSummary | null, tests: TestAssetSummary | null): FileNode['risk'] {
  if (summary?.coverage.missing_test_paths.includes(path) || tests?.coverage_gaps.includes(path)) return 'high'
  if (summary?.risk_signals.some(signal => signal.related_files.includes(path))) return 'medium'
  if (fileKind(path) === 'test') return 'low'
  return 'medium'
}

function buildFiles(changes: RecentAIChange[], summary: ChangeRiskSummary | null, tests: TestAssetSummary | null): FileNode[] {
  const paths = Array.from(new Set(changes.flatMap(change => change.changed_files))).sort()
  return paths.map(path => {
    const root = path.split('/')[0] || 'root'
    return {
      path,
      displayPath: path.split('/').slice(1).join('/') || path,
      root: `${root}/`,
      kind: fileKind(path),
      risk: fileRisk(path, summary, tests),
    }
  })
}

function riskBadge(risk: FileNode['risk']) {
  return risk === 'high' ? 'warning' : risk === 'low' ? 'stable' : 'running'
}

const FILE_DETAILS: Record<string, FileDetail> = {
  'backend/app/schemas/overview.py': {
    lead: '先按文件看 diff，再解释 diff 的产品意义：这个文件把测试资产管理正式变成 overview API 契约的一部分。',
    statusLabel: '需要 review',
    entrypoints: [
      { value: 'backend/app/schemas/overview.py', label: 'API schema' },
      { value: 'frontend/src/types/api.ts', label: 'TS contract' },
      { value: 'GET /api/overview', label: '新增字段' },
    ],
    tags: ['测试资产健康', '测试覆盖路径', '疑似失效测试'],
    coreMeaning: '这组文件的核心含义不是“加字段”，而是让用户在首页直接看到测试资产是否可信。',
    diffTitle: 'diff 摘要 · backend/app/schemas/overview.py',
    diffBadge: '+64 lines · additive contract',
    diffLines: [
      { type: 'context', line: '89', text: 'class ChangeRiskSummary(BaseModel):' },
      { type: 'context', line: '90', text: '    headline: ChangeRiskHeadline = ChangeRiskHeadline()' },
      { type: 'add', line: '+97', text: 'class TestAssetCapabilityCoverage(BaseModel):' },
      { type: 'add', line: '+98', text: '    capability_key: str = ""' },
      { type: 'add', line: '+99', text: '    business_capability: str = ""' },
      { type: 'add', line: '+100', text: '    coverage_status: Literal["covered", "partial", "missing", "unknown"] = "unknown"' },
      { type: 'add', line: '+101', text: '    technical_entrypoints: List[str] = Field(default_factory=list)' },
      { type: 'add', line: '+102', text: '    covered_paths: List[str] = Field(default_factory=list)' },
      { type: 'add', line: '+103', text: '    covering_tests: List[str] = Field(default_factory=list)' },
      { type: 'add', line: '+121', text: 'class TestAssetSummary(BaseModel):' },
      { type: 'add', line: '+122', text: '    health_status: Literal["healthy", "needs_maintenance", "high_risk", "unknown"] = "unknown"' },
      { type: 'add', line: '+129', text: '    capability_coverage: List[TestAssetCapabilityCoverage] = Field(default_factory=list)' },
      { type: 'add', line: '+130', text: '    test_files: List[TestAssetFile] = Field(default_factory=list)' },
      { type: 'context', line: '207', text: 'class OverviewResponse(BaseModel):' },
      { type: 'add', line: '+216', text: '    test_asset_summary: TestAssetSummary = TestAssetSummary()' },
    ],
    meaningTitle: '它不是普通字段追加，而是新增一个“测试资产治理”的 API 子模型。',
    meaningBullets: [
      { tone: 'good', text: '用户能看到测试覆盖了哪些业务能力和代码路径。' },
      { tone: 'warn', text: '前端需要兼容旧 snapshot 没有该字段的情况。' },
      { tone: 'warn', text: '字段是 additive，旧调用方不会因为响应多字段而破坏。' },
      { tone: 'risk', text: '如果 coverage_status 算错，会误导用户保留或淘汰测试。' },
    ],
    flow: [
      { title: 'overview.py', caption: '定义 TestAssetSummary' },
      { title: 'OverviewPage', caption: '展示测试资产健康卡' },
    ],
  },
  'backend/app/services/overview_inference/test_asset_summary.py': {
    lead: '这个文件不是展示层，而是把变更文件、验证证据和能力映射汇总成测试资产健康事实。',
    statusLabel: '核心逻辑',
    entrypoints: [
      { value: 'TestAssetSummaryBuilder.build()', label: '规则入口' },
      { value: 'verification_status', label: '证据来源' },
      { value: 'change_risk_summary.coverage', label: '覆盖缺口' },
    ],
    tags: ['规则事实', '测试维护', '覆盖缺口'],
    coreMeaning: '核心意义是先用规则给出可信事实，再让 Agent 只做业务影响和风险归纳。',
    diffTitle: 'diff 摘要 · backend/app/services/overview_inference/test_asset_summary.py',
    diffBadge: 'new file · rule engine',
    diffLines: [
      { type: 'add', line: '+8', text: 'class TestAssetSummaryBuilder:' },
      { type: 'add', line: '+12', text: '    def build(self, *, change_data, verification_data, capability_map):' },
      { type: 'add', line: '+19', text: '        changed_test_files = [path for path in changed_files if self._is_test_path(path)]' },
      { type: 'add', line: '+22', text: '        coverage_gaps = list(verification_data.get("missing_tests_for_changed_paths", []))' },
      { type: 'add', line: '+36', text: '        stale_or_invalid_test_count = sum(... maintenance_status in {"update", "retire"})' },
      { type: 'add', line: '+47', text: '            "recommended_actions": self._recommended_actions(...)' },
      { type: 'add', line: '+132', text: '            if coverage_gaps: invalidation_reasons.append(...)' },
    ],
    meaningTitle: '它把“测试文件是否还值得保留”从主观判断变成可解释的规则事实。',
    meaningBullets: [
      { tone: 'good', text: '先用规则计算覆盖缺口和维护状态，避免 Agent 直接拍脑袋。' },
      { tone: 'warn', text: '能把测试文件反向关联到业务能力、技术入口和被测路径。' },
      { tone: 'risk', text: '当前重复/低价值测试还没有语义去重，只能显示为后续增强项。' },
    ],
    flow: [
      { title: 'TestAssetSummaryBuilder', caption: '规则聚合' },
      { title: 'GET /api/overview', caption: '输出测试资产摘要' },
    ],
  },
  'frontend/src/types/api.ts': {
    lead: '这个文件把后端新增的测试资产模型翻译成前端可消费的 TS contract。',
    statusLabel: '需要 review',
    entrypoints: [
      { value: 'frontend/src/types/api.ts', label: 'TS contract' },
      { value: 'backend/app/schemas/overview.py', label: 'API schema' },
      { value: 'TestAssetSummaryCard', label: '消费字段' },
    ],
    tags: ['类型兼容', '旧 snapshot', '首页卡片数据源'],
    coreMeaning: '核心意义是降低前端误用字段的概率，并让首页能稳定读取测试资产治理数据。',
    diffTitle: 'diff 摘要 · frontend/src/types/api.ts',
    diffBadge: '+35 lines · typed contract',
    diffLines: [
      { type: 'add', line: '+42', text: 'export interface TestAssetCapabilityCoverage {' },
      { type: 'add', line: '+45', text: "  coverage_status: 'covered' | 'partial' | 'missing' | 'unknown'" },
      { type: 'add', line: '+49', text: '  covered_paths: string[]' },
      { type: 'add', line: '+50', text: '  covering_tests: string[]' },
      { type: 'add', line: '+64', text: 'export interface TestAssetSummary {' },
      { type: 'add', line: '+73', text: '  capability_coverage: TestAssetCapabilityCoverage[]' },
      { type: 'add', line: '+74', text: '  test_files: TestAssetFile[]' },
      { type: 'add', line: '+151', text: '  test_asset_summary?: TestAssetSummary' },
    ],
    meaningTitle: '它把 API 新字段变成前端明确契约，而不是让组件靠 any 猜结构。',
    meaningBullets: [
      { tone: 'good', text: '组件可以按业务能力、路径、测试文件三个层级展示测试资产。' },
      { tone: 'warn', text: '字段最好保持可选或有 fallback，避免旧数据直接把页面打挂。' },
      { tone: 'risk', text: '如果 TS contract 和后端 schema 漂移，首页会显示错误的测试状态。' },
    ],
    flow: [
      { title: 'api.ts', caption: '定义 TestAssetSummary 类型' },
      { title: 'TestAssetSummaryCard', caption: '按类型渲染' },
    ],
  },
}

function genericDetail(file: FileNode, capabilities: string[], entrypoints: string[], tests: string[]): FileDetail {
  const source = file.path.split('/').pop() || file.path
  const capabilityText = capabilities[0] ?? KIND_LABELS[file.kind]
  const entrypointText = entrypoints[0] ?? '内部实现或测试文件'
  const testText = tests[0] ?? '未找到直接关联测试'
  return {
    lead: '当前文件还没有专属归纳，先展示基于文件类型、入口和测试证据生成的通用解释。',
    statusLabel: file.risk === 'high' ? '高关注' : file.risk === 'low' ? '低风险' : '需 review',
    entrypoints: [
      { value: file.path, label: KIND_LABELS[file.kind] },
      { value: entrypointText, label: '关联入口' },
      { value: testText, label: '测试证据' },
    ],
    tags: [capabilityText, KIND_LABELS[file.kind], '文件级 diff'],
    coreMeaning: '这里不能复用其他文件的解释。即使缺少 Agent 专属归纳，也必须让路径、入口、能力和测试证据跟当前文件一致。',
    diffTitle: `diff 摘要 · ${file.path}`,
    diffBadge: 'file-specific summary pending',
    diffLines: [
      { type: 'context', line: '…', text: '专属 diff 摘要待由规则层从 git diff / file diff API 生成' },
      { type: 'add', line: '+', text: file.path },
      { type: 'context', line: '…', text: '这里不应复用其他文件的产品解释' },
    ],
    meaningTitle: '当前文件需要展示自己的 diff 意义，而不是复用上一个文件的产品解释。',
    meaningBullets: [
      { tone: 'good', text: '文件路径、类型和入口至少必须随选择变化。' },
      { tone: 'warn', text: '专属业务意义需要 Agent 基于规则事实归纳。' },
      { tone: 'risk', text: '如果复用其他文件解释，会误导 review 顺序。' },
    ],
    flow: [
      { title: source, caption: KIND_LABELS[file.kind] },
      { title: 'Review', caption: '确认该文件的真实影响' },
    ],
  }
}

function detailFromSummary(summary: FileReviewSummary): FileDetail {
  const firstFlowTitle = summary.path.split('/').pop() || summary.path
  const secondFlowTitle = summary.related_entrypoints[0] ?? 'Review'
  return {
    lead: summary.product_meaning,
    statusLabel: summary.risk_level === 'high' ? '高关注' : summary.risk_level === 'low' ? '低风险' : '需 review',
    entrypoints: [
      { value: summary.path, label: summary.file_role },
      ...summary.related_entrypoints.map(value => ({ value, label: '技术入口' })),
      ...summary.related_tests.slice(0, 1).map(value => ({ value, label: '测试证据' })),
    ],
    tags: [...summary.related_capabilities, ...summary.review_focus.slice(0, 2)].filter(Boolean),
    coreMeaning: summary.product_meaning,
    diffTitle: `diff 摘要 · ${summary.path}`,
    diffBadge: summary.diff_summary,
    diffLines: summary.diff_snippets.map(item => ({
      type: item.type,
      line: item.line,
      text: item.text,
    })),
    meaningTitle: summary.product_meaning,
    meaningBullets: (summary.intent_evidence ?? [])
      .slice(0, 2)
      .map(text => ({ tone: 'good' as const, text: `依据：${text}` })),
    flow: [
      { title: firstFlowTitle, caption: summary.file_role },
      { title: secondFlowTitle, caption: '关联入口/Review' },
    ],
  }
}

function matchingCapabilities(file: FileNode, changes: RecentAIChange[], summary: ChangeRiskSummary | null): string[] {
  const fromChanges = changes
    .filter(change => change.changed_files.includes(file.path))
    .flatMap(change => change.affected_capabilities)
  const fromSummary = summary?.existing_feature_impact.affected_capabilities
    .filter(item => item.changed_files.includes(file.path))
    .map(item => item.name) ?? []
  return Array.from(new Set([...fromChanges, ...fromSummary])).filter(Boolean)
}

function matchingEntryPoints(file: FileNode, changes: RecentAIChange[], summary: ChangeRiskSummary | null): string[] {
  const fromChanges = changes
    .filter(change => change.changed_files.includes(file.path))
    .flatMap(change => change.technical_entrypoints.length ? change.technical_entrypoints : change.affected_entrypoints)
  const fromCapabilities = summary?.existing_feature_impact.affected_capabilities
    .filter(item => item.changed_files.includes(file.path))
    .flatMap(item => item.technical_entrypoints) ?? []
  return Array.from(new Set([...fromChanges, ...fromCapabilities])).filter(Boolean)
}

function matchingTests(file: FileNode, changes: RecentAIChange[], tests: TestAssetSummary | null): string[] {
  const fromChanges = changes
    .filter(change => change.changed_files.includes(file.path))
    .flatMap(change => change.linked_tests)
  const related = tests?.test_files.filter(item => item.path === file.path || item.covered_paths.includes(file.path)) ?? []
  return Array.from(new Set([...fromChanges, ...related.map(item => item.path)])).filter(Boolean)
}

export function ProjectStructureChangeCard({ changes, fileReviewSummaries, changeRiskSummary, testAssetSummary, loading }: Props) {
  const files = buildFiles(changes, changeRiskSummary, testAssetSummary)
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const selected = files.find(file => file.path === selectedPath) ?? files[0] ?? null
  const roots = Array.from(new Set(files.map(file => file.root)))

  if (loading) {
    return (
      <CardShell title="项目结构变更">
        <div className={styles.loading}>
          <SkeletonBlock height={24} width="40%" />
          <SkeletonBlock height={14} lines={4} />
        </div>
      </CardShell>
    )
  }

  if (!selected) {
    return (
      <CardShell title="项目结构变更">
        <EmptyState message="当前没有可按项目结构展示的变更文件。" />
      </CardShell>
    )
  }

  const capabilities = matchingCapabilities(selected, changes, changeRiskSummary)
  const entrypoints = matchingEntryPoints(selected, changes, changeRiskSummary)
  const tests = matchingTests(selected, changes, testAssetSummary)
  const backendSummary = fileReviewSummaries.find(item => item.path === selected.path)
  const detail = backendSummary ? detailFromSummary(backendSummary) : (FILE_DETAILS[selected.path] ?? genericDetail(selected, capabilities, entrypoints, tests))

  return (
    <CardShell
      title="项目结构变更"
      subtitle={`${files.length} 个变更文件 · 先按目录定位，再看 diff 意义`}
      badge={<StatusBadge status={riskBadge(selected.risk)} label={KIND_LABELS[selected.kind]} />}
    >
      <div className={styles.layout}>
        <aside className={styles.tree} aria-label="项目结构目录树">
          {roots.map(root => (
            <section key={root} className={styles.rootGroup}>
              <div className={styles.rootHeader}>
                <strong>{root}</strong>
                <span>{files.filter(file => file.root === root).length} files</span>
              </div>
              {files.filter(file => file.root === root).map(file => (
                <button
                  key={file.path}
                  type="button"
                  className={`${styles.fileNode} ${file.path === selected.path ? styles.active : ''}`}
                  onClick={() => setSelectedPath(file.path)}
                >
                  <span className={`${styles.dot} ${styles[file.risk]}`} />
                  <span className={styles.fileName}>{file.displayPath}</span>
                  <span className={styles.kind}>{KIND_LABELS[file.kind]}</span>
                </button>
              ))}
            </section>
          ))}
        </aside>

        <section className={styles.detail}>
          <div className={styles.detailHeader}>
            <div>
              <p className={styles.kicker}>当前文件</p>
              <h3>{selected.path}</h3>
              <p className={styles.lead}>{detail.lead}</p>
            </div>
            <StatusBadge status={riskBadge(selected.risk)} label={detail.statusLabel} />
          </div>

          <div className={styles.diffCard}>
            <div className={styles.diffHeader}>
              <strong>{detail.diffTitle}</strong>
              <span>{detail.diffBadge}</span>
            </div>
            <div className={styles.diffGrid}>
              <div className={styles.diffLines} aria-label="文件 diff 滚动窗口">
                {detail.diffLines.map((line, index) => (
                  <div
                    key={`${line.line}-${index}`}
                    className={`${styles.diffLine} ${
                      line.type === 'add' ? styles.add : line.type === 'delete' ? styles.delete : styles.context
                    }`}
                  >
                    <span>{line.line}</span>
                    <code>{line.text}</code>
                  </div>
                ))}
              </div>
              <div className={styles.meaningPanel}>
                <p className={styles.kicker}>这段 diff 的意义</p>
                <strong>{detail.meaningTitle}</strong>
                {detail.meaningBullets.length > 0 && (
                  <div className={styles.meaningList}>
                    {detail.meaningBullets.map(item => (
                      <div key={item.text} className={styles.meaningItem}>
                        <span className={`${styles.signal} ${styles[item.tone]}`} />
                        <span>{item.text}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className={styles.flow}>
            {detail.flow.map((item, index) => (
              <div key={item.title} className={styles.flowItem}>
                <div className={styles.node}>
                  <code>{item.title}</code>
                  <span>{item.caption}</span>
                </div>
                {index < detail.flow.length - 1 && <span className={styles.arrow}>→</span>}
              </div>
            ))}
          </div>

          <div className={styles.columns}>
            <div className={styles.box}>
              <p className={styles.kicker}>规则识别到的测试覆盖</p>
              {tests.length > 0 ? tests.map(item => <code key={item}>{item}</code>) : <span className={styles.empty}>未找到直接关联测试</span>}
            </div>
          </div>
        </section>
      </div>
    </CardShell>
  )
}
