import type { JobState } from '../../types/api'
import styles from './RebuildProgress.module.css'

const STEP_LABELS: Record<string, string> = {
  init: '正在初始化…',
  capture_working_tree: '正在捕获工作区状态…',
  build_graph_snapshot: '正在解析代码图谱…',
  analyze_pending_change: '正在分析差异…',
  aggregate_verification: '正在汇总测试结果…',
  infer_overview: '正在生成总览…',
  prepare_agent_context: '正在准备 Agent 分析上下文…',
  agent_round_1: '正在进行 Agent 首轮分析…',
  agent_round_2: '正在进行 Agent 补充分析…',
  validate_agent_output: '正在校验 Agent 输出…',
  build_overview_payload: '正在组装总览结果…',
  done: '正在收尾…',
}

interface Props {
  job: JobState | null
}

export function RebuildProgress({ job }: Props) {
  if (!job) return null
  const label = STEP_LABELS[job.step] ?? job.message ?? '处理中…'
  const pct = Math.min(100, Math.max(0, job.progress))

  return (
    <div className={styles.wrap}>
      <div className={styles.track}>
        <div className={styles.fill} style={{ width: `${pct}%` }} />
      </div>
      <span className={styles.label}>{label}</span>
    </div>
  )
}
