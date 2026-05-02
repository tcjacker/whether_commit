import type { JobState } from '../../types/api'
import type { Language } from '../../i18n'
import styles from './RebuildProgress.module.css'

const STEP_LABELS: Record<Language, Record<string, string>> = {
  'zh-CN': {
    init: '正在初始化...',
    capture_working_tree: '正在捕获工作区状态...',
    build_graph_snapshot: '正在解析代码图谱...',
    analyze_pending_change: '正在分析差异...',
    aggregate_verification: '正在汇总测试结果...',
    build_assessment: '正在生成 Agentic Change Assessment...',
    done: '正在收尾...',
  },
  'en-US': {
    init: 'Initializing...',
    capture_working_tree: 'Capturing working tree...',
    build_graph_snapshot: 'Parsing code graph...',
    analyze_pending_change: 'Analyzing diff...',
    aggregate_verification: 'Aggregating verification...',
    build_assessment: 'Generating Agentic Change Assessment...',
    done: 'Finishing...',
  },
}

interface Props {
  job: JobState | null
  language?: Language
}

export function RebuildProgress({ job, language = 'zh-CN' }: Props) {
  if (!job) return null
  const label = STEP_LABELS[language][job.step] ?? job.message ?? (language === 'zh-CN' ? '处理中...' : 'Processing...')
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
