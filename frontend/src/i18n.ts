export type Language = 'zh-CN' | 'en-US'

type MessageKey =
  | 'agentAssessmentAccepted'
  | 'agentAssessmentRunning'
  | 'agentOverallAssessment'
  | 'agentClaims'
  | 'changedFiles'
  | 'codeChangeOverview'
  | 'codexRecords'
  | 'confidence'
  | 'coverage'
  | 'english'
  | 'evidence'
  | 'evidenceGrade'
  | 'factChecks'
  | 'hunk'
  | 'language'
  | 'loadingAssessment'
  | 'mismatch'
  | 'mismatches'
  | 'noAgentProvenance'
  | 'noChangedFiles'
  | 'noClaimFactMismatch'
  | 'noFileSelected'
  | 'noStructuredGoal'
  | 'noTestCommands'
  | 'onlyGitDiffEvidence'
  | 'priority'
  | 'provenance'
  | 'rebuild'
  | 'rebuilding'
  | 'relatedTests'
  | 'review'
  | 'reviewSignals'
  | 'reviewSignalsDescription'
  | 'risk'
  | 'ruleFallback'
  | 'runCodexAssessment'
  | 'selectFileForDiff'
  | 'simplifiedChinese'
  | 'sources'
  | 'symbols'
  | 'testEvidence'
  | 'testExecution'
  | 'testFiles'
  | 'tests'
  | 'thisRoundGoal'
  | 'unknown'
  | 'unknowns'
  | 'verdict'

const STORAGE_KEY = 'assessment.language'

const MESSAGES: Record<Language, Record<MessageKey, string>> = {
  'zh-CN': {
    agentAssessmentAccepted: 'Agent 分析 · Codex',
    agentAssessmentRunning: 'Agent 分析运行中 · Codex',
    agentOverallAssessment: 'Agent 总体评估',
    agentClaims: 'Agent 声明',
    changedFiles: '变更文件',
    codeChangeOverview: '代码变更总览',
    codexRecords: 'Codex 聊天和操作记录',
    confidence: '置信度',
    coverage: '覆盖',
    english: 'English',
    evidence: '证据',
    evidenceGrade: '证据等级',
    factChecks: '事实校验',
    hunk: 'Hunk',
    language: '语言',
    loadingAssessment: '正在加载评估...',
    mismatch: '不一致',
    mismatches: '不一致项',
    noAgentProvenance: '此文件未关联到 agent 专属溯源。',
    noChangedFiles: '没有变更文件。',
    noClaimFactMismatch: '未检测到 claim/fact 不一致。',
    noFileSelected: '未选择文件。',
    noStructuredGoal: '未捕获到结构化 Codex 设计目标',
    noTestCommands: '未捕获到已执行测试命令。',
    onlyGitDiffEvidence: '当前只有 git diff 证据；审查此文件时不要依赖 agent 消息或工具归因。',
    priority: '优先级',
    provenance: '溯源',
    rebuild: '开始重建',
    rebuilding: '正在重建...',
    relatedTests: '相关测试',
    review: '审查',
    reviewSignals: 'v0.2 审查信号',
    reviewSignalsDescription: '提交前对当前 hunk 做 claim/fact 校验。',
    risk: '风险',
    ruleFallback: '规则兜底',
    runCodexAssessment: '运行 Codex 分析',
    selectFileForDiff: '选择一个文件查看 diff。',
    simplifiedChinese: '简体中文',
    sources: '来源',
    symbols: '符号',
    testEvidence: '测试证据',
    testExecution: '测试执行情况',
    testFiles: '测试文件',
    tests: '测试',
    thisRoundGoal: '本轮目标',
    unknown: '未知',
    unknowns: '未知项',
    verdict: '结论',
  },
  'en-US': {
    agentAssessmentAccepted: 'Agent assessment · Codex',
    agentAssessmentRunning: 'Agent assessment running · Codex',
    agentOverallAssessment: 'Agent Overall Assessment',
    agentClaims: 'Agent Claims',
    changedFiles: 'Changed Files',
    codeChangeOverview: 'Code Change Overview',
    codexRecords: 'Codex Chat and Operation Records',
    confidence: 'confidence',
    coverage: 'Coverage',
    english: 'English',
    evidence: 'Evidence',
    evidenceGrade: 'Evidence grade',
    factChecks: 'Fact Checks',
    hunk: 'Hunk',
    language: 'Language',
    loadingAssessment: 'Loading assessment...',
    mismatch: 'mismatch',
    mismatches: 'Mismatches',
    noAgentProvenance: 'No agent-specific provenance was linked to this file.',
    noChangedFiles: 'No changed files.',
    noClaimFactMismatch: 'No claim/fact mismatch was detected.',
    noFileSelected: 'No file selected.',
    noStructuredGoal: 'No structured Codex design goal was captured.',
    noTestCommands: 'No executed test command was captured.',
    onlyGitDiffEvidence: 'Only git diff evidence is available; review this file without relying on agent message/tool attribution.',
    priority: 'Priority',
    provenance: 'Provenance',
    rebuild: 'Start rebuild',
    rebuilding: 'Rebuilding...',
    relatedTests: 'Related tests',
    review: 'Review',
    reviewSignals: 'v0.2 Review Signals',
    reviewSignalsDescription: 'Claim/fact checks for this hunk before commit.',
    risk: 'Risk',
    ruleFallback: 'Rule-based fallback',
    runCodexAssessment: 'Run Codex Assessment',
    selectFileForDiff: 'Select a file to review its diff.',
    simplifiedChinese: '简体中文',
    sources: 'Sources',
    symbols: 'Symbols',
    testEvidence: 'Test Evidence',
    testExecution: 'Test Execution',
    testFiles: 'Test Files',
    tests: 'Tests',
    thisRoundGoal: 'This Round Goal',
    unknown: 'unknown',
    unknowns: 'Unknowns',
    verdict: 'Verdict',
  },
}

const STATUS_LABELS: Record<Language, Record<string, string>> = {
  'zh-CN': {
    passed: '通过',
    failed: '失败',
    unknown: '未知',
    warning: '警告',
    running: '运行中',
    recently_changed: '最近变更',
    stable: '稳定',
    needs_review: '需复查',
    partial: '部分完成',
    partial_success: '部分成功',
    success: '成功',
    ready: '已就绪',
  },
  'en-US': {
    passed: 'passed',
    failed: 'failed',
    unknown: 'unknown',
    warning: 'warning',
    running: 'running',
    recently_changed: 'recently changed',
    stable: 'stable',
    needs_review: 'needs review',
    partial: 'partial',
    partial_success: 'partial success',
    success: 'success',
    ready: 'ready',
  },
}

const CONFIDENCE_LABELS: Record<Language, Record<string, string>> = {
  'zh-CN': { high: '高', medium: '中', low: '低' },
  'en-US': { high: 'high', medium: 'medium', low: 'low' },
}

const CHANGE_TYPE_LABELS: Record<Language, Record<string, string>> = {
  'zh-CN': {
    flow_change: '流程变更',
    contract_change: '契约变更',
    job_change: '任务变更',
    code_modification: '代码修改',
  },
  'en-US': {
    flow_change: 'flow change',
    contract_change: 'contract change',
    job_change: 'job change',
    code_modification: 'code modification',
  },
}

const NODE_TYPE_LABELS: Record<Language, Record<string, string>> = {
  'zh-CN': {
    router: '路由',
    'api handler': '接口处理器',
    service: '服务',
    repository: '仓储',
    'db model': '数据库模型',
    worker: '后台任务',
    'external integration': '外部集成',
    config: '配置',
    gateway: '网关',
    database: '数据库',
    external: '外部依赖',
    cache: '缓存',
    queue: '队列',
  },
  'en-US': {
    router: 'router',
    'api handler': 'API handler',
    service: 'service',
    repository: 'repository',
    'db model': 'database model',
    worker: 'worker',
    'external integration': 'external integration',
    config: 'config',
    gateway: 'gateway',
    database: 'database',
    external: 'external dependency',
    cache: 'cache',
    queue: 'queue',
  },
}

const CRITICALITY_LABELS: Record<Language, Record<string, string>> = {
  'zh-CN': { high: '高', medium: '中', low: '低', critical: '关键' },
  'en-US': { high: 'high', medium: 'medium', low: 'low', critical: 'critical' },
}

export function isLanguage(value: string | null | undefined): value is Language {
  return value === 'zh-CN' || value === 'en-US'
}

export function readStoredLanguage(): Language {
  if (typeof window === 'undefined') return 'zh-CN'
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return isLanguage(stored) ? stored : 'zh-CN'
}

export function storeLanguage(language: Language): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEY, language)
}

export function t(language: Language, key: MessageKey): string {
  return (MESSAGES[language] ?? MESSAGES['zh-CN'])[key] ?? key
}

export function formatValue(value: string, language: Language): string {
  const normalized = value.replaceAll('_', ' ')
  return language === 'zh-CN' ? normalized : normalized
}

export function formatCount(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`
}

export function formatMismatchCount(count: number, language: Language): string {
  if (language === 'zh-CN') return `${count} 个不一致`
  return formatCount(count, 'mismatch')
}

export function zhStatus(status: string, language: Language = 'zh-CN'): string {
  return STATUS_LABELS[language][status] ?? status.replace(/_/g, ' ')
}

export function zhConfidence(confidence: string, language: Language = 'zh-CN'): string {
  return CONFIDENCE_LABELS[language][confidence] ?? confidence
}

export function zhChangeType(changeType: string, language: Language = 'zh-CN'): string {
  return CHANGE_TYPE_LABELS[language][changeType] ?? changeType.replace(/_/g, ' ')
}

export function zhNodeType(nodeType: string, language: Language = 'zh-CN'): string {
  return NODE_TYPE_LABELS[language][nodeType.toLowerCase()] ?? nodeType
}

export function zhCriticality(criticality: string, language: Language = 'zh-CN'): string {
  return CRITICALITY_LABELS[language][criticality] ?? criticality
}

export function zhCount(count: number, noun: string, language: Language = 'zh-CN'): string {
  return language === 'zh-CN' ? `${count} 个${noun}` : formatCount(count, noun)
}

export function zhChangeTitle(title: string, language: Language = 'zh-CN'): string {
  const match = title.match(/^Workspace diff \((\d+) files\)$/)
  if (match && language === 'zh-CN') {
    return `工作区差异（${match[1]} 个文件）`
  }
  return title
}
