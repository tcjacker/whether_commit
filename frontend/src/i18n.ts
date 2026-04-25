const STATUS_LABELS: Record<string, string> = {
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
}

const CONFIDENCE_LABELS: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
}

const CHANGE_TYPE_LABELS: Record<string, string> = {
  flow_change: '流程变更',
  contract_change: '契约变更',
  job_change: '任务变更',
  code_modification: '代码修改',
}

const NODE_TYPE_LABELS: Record<string, string> = {
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
}

const CRITICALITY_LABELS: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
  critical: '关键',
}

export function zhStatus(status: string): string {
  return STATUS_LABELS[status] ?? status
}

export function zhConfidence(confidence: string): string {
  return CONFIDENCE_LABELS[confidence] ?? confidence
}

export function zhChangeType(changeType: string): string {
  return CHANGE_TYPE_LABELS[changeType] ?? changeType.replace(/_/g, ' ')
}

export function zhNodeType(nodeType: string): string {
  return NODE_TYPE_LABELS[nodeType.toLowerCase()] ?? nodeType
}

export function zhCriticality(criticality: string): string {
  return CRITICALITY_LABELS[criticality] ?? criticality
}

export function zhCount(count: number, noun: string): string {
  return `${count} 个${noun}`
}

export function zhChangeTitle(title: string): string {
  const match = title.match(/^Workspace diff \((\d+) files\)$/)
  if (match) {
    return `工作区差异（${match[1]} 个文件）`
  }
  return title
}
