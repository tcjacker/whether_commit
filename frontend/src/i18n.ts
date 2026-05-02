export type Language = 'zh-CN' | 'en-US'

type MessageKey =
  | 'agentAssessmentAccepted'
  | 'agentAssessmentRunning'
  | 'agentOverallAssessment'
  | 'agentClaims'
  | 'agentAnalysis'
  | 'agentAnalyze'
  | 'agentAnalysisUnavailable'
  | 'agentAnalysisRefreshed'
  | 'agentTestResultAnalysis'
  | 'analyzingStoredTestResult'
  | 'analyzingTestRun'
  | 'basis'
  | 'cancel'
  | 'caseNameSource'
  | 'changedFiles'
  | 'close'
  | 'command'
  | 'confirmTestRerun'
  | 'codeChangeOverview'
  | 'codexRecords'
  | 'confidence'
  | 'coverage'
  | 'coverageGaps'
  | 'coveredChangedCode'
  | 'coveredScenarios'
  | 'data'
  | 'english'
  | 'evidence'
  | 'evidenceBasis'
  | 'evidenceGrade'
  | 'executedCases'
  | 'factChecks'
  | 'hunk'
  | 'language'
  | 'loadingAssessment'
  | 'mismatch'
  | 'mismatches'
  | 'noAgentProvenance'
  | 'noChangedFiles'
  | 'noClaimFactMismatch'
  | 'noCoveredChangedCode'
  | 'noCoveredScenarios'
  | 'noFileSelected'
  | 'noIndividualCases'
  | 'noRecommendedCommand'
  | 'noRawOutput'
  | 'noRelatedAgentClaims'
  | 'noStoredTestResult'
  | 'noStructuredGoal'
  | 'noTestCommands'
  | 'noTestExecutionEvidence'
  | 'noUnknownsRecorded'
  | 'onlyGitDiffEvidence'
  | 'priority'
  | 'provenance'
  | 'rawOutput'
  | 'rebuild'
  | 'rebuilding'
  | 'recommendedCommands'
  | 'relatedTests'
  | 'rerun'
  | 'rerunRecommendedTest'
  | 'review'
  | 'reviewSignals'
  | 'reviewSignalsDescription'
  | 'risk'
  | 'ruleFallback'
  | 'ruleAnalysis'
  | 'runTest'
  | 'running'
  | 'runningTestCommand'
  | 'runCodexAssessment'
  | 'selectFileForDiff'
  | 'selectTestCase'
  | 'selectTestCaseCode'
  | 'selectTestCaseEvidence'
  | 'selectTestCaseResult'
  | 'simplifiedChinese'
  | 'sources'
  | 'source'
  | 'symbols'
  | 'scope'
  | 'status'
  | 'statusEvidence'
  | 'testCases'
  | 'testData'
  | 'testEvidence'
  | 'testExecution'
  | 'testFiles'
  | 'testIntent'
  | 'testManagement'
  | 'testPageEmptyBody'
  | 'testPageEmptyTitle'
  | 'testPageTitle'
  | 'testResult'
  | 'testResultAnalysis'
  | 'testRunCommandDescription'
  | 'testRunRecommendedDescription'
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
    agentAnalysis: 'Agent 分析',
    agentAnalyze: 'Agent 分析',
    agentAnalysisUnavailable: '此评估暂不支持 Agent 分析。',
    agentAnalysisRefreshed: 'Agent 分析刚刚刷新。',
    agentTestResultAnalysis: 'Agent 测试结果分析',
    analyzingStoredTestResult: '正在分析已存储的测试结果、执行用例和测试代码...',
    analyzingTestRun: '正在分析已执行用例、测试数据和覆盖场景...',
    basis: '依据',
    cancel: '取消',
    caseNameSource: '用例名称来源',
    changedFiles: '变更文件',
    close: '关闭',
    command: '命令',
    confirmTestRerun: '确认重新运行测试',
    codeChangeOverview: '代码变更总览',
    codexRecords: 'Codex 聊天和操作记录',
    confidence: '置信度',
    coverage: '覆盖',
    coverageGaps: '覆盖缺口',
    coveredChangedCode: '覆盖的变更代码',
    coveredScenarios: '覆盖场景',
    data: '数据',
    english: 'English',
    evidence: '证据',
    evidenceBasis: '证据依据',
    evidenceGrade: '证据等级',
    executedCases: '已执行用例',
    factChecks: '事实校验',
    hunk: 'Hunk',
    language: '语言',
    loadingAssessment: '正在加载评估...',
    mismatch: '不一致',
    mismatches: '不一致项',
    noAgentProvenance: '此文件未关联到 agent 专属溯源。',
    noChangedFiles: '没有变更文件。',
    noClaimFactMismatch: '未检测到 claim/fact 不一致。',
    noCoveredChangedCode: '未识别出覆盖的变更代码。',
    noCoveredScenarios: '未提取出覆盖场景。',
    noFileSelected: '未选择文件。',
    noIndividualCases: '未捕获到单个用例名称。',
    noRecommendedCommand: '没有可用的推荐命令。',
    noRawOutput: '未捕获原始输出。',
    noRelatedAgentClaims: '没有相关 Agent 声明。',
    noStoredTestResult: '没有已存储的测试结果。请先重新运行测试，再分析结果。',
    noStructuredGoal: '未捕获到结构化 Codex 设计目标',
    noTestCommands: '未捕获到已执行测试命令。',
    noTestExecutionEvidence: '还没有测试执行证据',
    noUnknownsRecorded: '没有记录未知项。',
    onlyGitDiffEvidence: '当前只有 git diff 证据；审查此文件时不要依赖 agent 消息或工具归因。',
    priority: '优先级',
    provenance: '溯源',
    rawOutput: '原始输出',
    rebuild: '开始重建',
    rebuilding: '正在重建...',
    recommendedCommands: '推荐命令',
    relatedTests: '相关测试',
    rerun: '重新运行',
    rerunRecommendedTest: '重新运行推荐测试',
    review: '审查',
    reviewSignals: 'v0.2 审查信号',
    reviewSignalsDescription: '提交前对当前 hunk 做 claim/fact 校验。',
    risk: '风险',
    ruleFallback: '规则兜底',
    ruleAnalysis: '规则分析',
    runTest: '运行测试',
    running: '运行中',
    runningTestCommand: '正在运行测试命令...',
    runCodexAssessment: '运行 Codex 分析',
    selectFileForDiff: '选择一个文件查看 diff。',
    selectTestCase: '选择测试用例',
    selectTestCaseCode: '选择一个测试用例查看代码。',
    selectTestCaseEvidence: '选择一个测试用例查看证据。',
    selectTestCaseResult: '选择一个测试用例查看最新结果。',
    simplifiedChinese: '简体中文',
    sources: '来源',
    source: '来源',
    symbols: '符号',
    scope: '范围',
    status: '状态',
    statusEvidence: '状态证据',
    testCases: '测试用例',
    testData: '测试数据',
    testEvidence: '测试证据',
    testExecution: '测试执行情况',
    testFiles: '测试文件',
    testIntent: '测试意图',
    testManagement: '测试管理',
    testPageEmptyBody: '请在包含测试文件变更的工作区中重建，或使用包含当前 test-management 实现快照的 worktree URL。',
    testPageEmptyTitle: '此评估中没有变更测试用例',
    testPageTitle: 'AI 编写的测试用例',
    testResult: '测试结果',
    testResultAnalysis: '测试结果分析',
    testRunCommandDescription: '这会在所选工作区中执行推荐的测试命令。',
    testRunRecommendedDescription: '这会在当前工作区运行生成的命令。',
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
    agentAnalysis: 'Agent Analysis',
    agentAnalyze: 'Agent Analyze',
    agentAnalysisUnavailable: 'Agent analysis is unavailable for this assessment.',
    agentAnalysisRefreshed: 'Agent analysis refreshed just now.',
    agentTestResultAnalysis: 'Agent Test Result Analysis',
    analyzingStoredTestResult: 'Analyzing stored test result, executed cases, and test code...',
    analyzingTestRun: 'Analyzing executed cases, test data, and covered scenarios...',
    basis: 'Basis',
    cancel: 'Cancel',
    caseNameSource: 'Case name source',
    changedFiles: 'Changed Files',
    close: 'Close',
    command: 'Command',
    confirmTestRerun: 'Confirm Test ReRun',
    codeChangeOverview: 'Code Change Overview',
    codexRecords: 'Codex Chat and Operation Records',
    confidence: 'confidence',
    coverage: 'Coverage',
    coverageGaps: 'Coverage Gaps',
    coveredChangedCode: 'Covered Changed Code',
    coveredScenarios: 'Covered Scenarios',
    data: 'Data',
    english: 'English',
    evidence: 'Evidence',
    evidenceBasis: 'Evidence Basis',
    evidenceGrade: 'Evidence grade',
    executedCases: 'Executed Cases',
    factChecks: 'Fact Checks',
    hunk: 'Hunk',
    language: 'Language',
    loadingAssessment: 'Loading assessment...',
    mismatch: 'mismatch',
    mismatches: 'Mismatches',
    noAgentProvenance: 'No agent-specific provenance was linked to this file.',
    noChangedFiles: 'No changed files.',
    noClaimFactMismatch: 'No claim/fact mismatch was detected.',
    noCoveredChangedCode: 'No covered changed code was identified.',
    noCoveredScenarios: 'No covered scenarios were extracted.',
    noFileSelected: 'No file selected.',
    noIndividualCases: 'No individual case names were captured.',
    noRecommendedCommand: 'No recommended command is available.',
    noRawOutput: 'No raw output captured.',
    noRelatedAgentClaims: 'No related agent claims.',
    noStoredTestResult: 'No stored test result is available. Run ReRun first, then analyze the result.',
    noStructuredGoal: 'No structured Codex design goal was captured.',
    noTestCommands: 'No executed test command was captured.',
    noTestExecutionEvidence: 'No execution evidence yet',
    noUnknownsRecorded: 'No unknowns recorded.',
    onlyGitDiffEvidence: 'Only git diff evidence is available; review this file without relying on agent message/tool attribution.',
    priority: 'Priority',
    provenance: 'Provenance',
    rawOutput: 'Raw Output',
    rebuild: 'Start rebuild',
    rebuilding: 'Rebuilding...',
    recommendedCommands: 'Recommended Commands',
    relatedTests: 'Related tests',
    rerun: 'ReRun',
    rerunRecommendedTest: 'ReRun Recommended Test',
    review: 'Review',
    reviewSignals: 'v0.2 Review Signals',
    reviewSignalsDescription: 'Claim/fact checks for this hunk before commit.',
    risk: 'Risk',
    ruleFallback: 'Rule-based fallback',
    ruleAnalysis: 'Rule Analysis',
    runTest: 'Run Test',
    running: 'Running',
    runningTestCommand: 'Running test command...',
    runCodexAssessment: 'Run Codex Assessment',
    selectFileForDiff: 'Select a file to review its diff.',
    selectTestCase: 'Select a test case',
    selectTestCaseCode: 'Select a test case to inspect its code.',
    selectTestCaseEvidence: 'Select a test case to inspect its evidence.',
    selectTestCaseResult: 'Select a test case to inspect its latest result.',
    simplifiedChinese: '简体中文',
    sources: 'Sources',
    source: 'Source',
    symbols: 'Symbols',
    scope: 'Scope',
    status: 'Status',
    statusEvidence: 'Status evidence',
    testCases: 'Test Cases',
    testData: 'Test Data',
    testEvidence: 'Test Evidence',
    testExecution: 'Test Execution',
    testFiles: 'Test Files',
    testIntent: 'Test Intent',
    testManagement: 'Test Management',
    testPageEmptyBody: 'Rebuild from a workspace with changed test files, or use the worktree URL that contains the current test-management implementation snapshot.',
    testPageEmptyTitle: 'No changed test cases in this assessment',
    testPageTitle: 'AI-Written Test Cases',
    testResult: 'Test Result',
    testResultAnalysis: 'Test Result Analysis',
    testRunCommandDescription: 'This will execute the recommended test command in the selected workspace.',
    testRunRecommendedDescription: 'This will run the generated command in the current workspace.',
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
    added: '新增',
    modified: '修改',
    deleted: '删除',
    direct: '直接',
    indirect: '间接',
    inferred: '推断',
    claimed: '声明',
    not_run: '未运行',
    certain: '确定',
    heuristic: '启发式',
    fallback: '兜底',
    generated: '生成',
    rule_derived: '规则推导',
    runner_output: '运行器输出',
    collect_only: '仅收集',
    test_file_parse: '测试文件解析',
    test_case: '测试用例',
    test_file: '测试文件',
    changed_area: '变更区域',
    assessment: '评估',
    rerun: '重新运行',
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
    added: 'added',
    modified: 'modified',
    deleted: 'deleted',
    direct: 'direct',
    indirect: 'indirect',
    inferred: 'inferred',
    claimed: 'claimed',
    not_run: 'not run',
    certain: 'certain',
    heuristic: 'heuristic',
    fallback: 'fallback',
    generated: 'generated',
    rule_derived: 'rule derived',
    runner_output: 'runner output',
    collect_only: 'collect-only discovery',
    test_file_parse: 'test file parse',
    test_case: 'test case',
    test_file: 'test file',
    changed_area: 'changed area',
    assessment: 'assessment',
    rerun: 'rerun',
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
