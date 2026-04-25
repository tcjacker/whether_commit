import type { JobState } from '../../types/api'
import styles from './RebuildProgress.module.css'

const STEP_LABELS: Record<string, string> = {
  init: '正在初始化…',
  capture_working_tree: '正在捕获工作区状态…',
  build_graph_snapshot: '正在解析代码图谱…',
  analyze_pending_change: '正在分析差异…',
  aggregate_verification: '正在汇总测试结果…',
  build_assessment: '正在生成 Agentic Change Assessment…',
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
