import type { JobState } from '../../types/api'
import styles from './RebuildProgress.module.css'

const STEP_LABELS: Record<string, string> = {
  init: 'Initializing…',
  capture_working_tree: 'Capturing working tree…',
  build_graph_snapshot: 'Parsing code graph…',
  analyze_pending_change: 'Analyzing diffs…',
  aggregate_verification: 'Collecting test results…',
  infer_overview: 'Inferring overview…',
  done: 'Finalizing…',
}

interface Props {
  job: JobState | null
}

export function RebuildProgress({ job }: Props) {
  if (!job) return null
  const label = STEP_LABELS[job.step] ?? job.message ?? 'Working…'
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
