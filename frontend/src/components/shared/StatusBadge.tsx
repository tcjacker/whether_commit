import styles from './StatusBadge.module.css'

type Status = 'passed' | 'failed' | 'unknown' | 'warning' | 'running' |
              'recently_changed' | 'stable' | 'needs_review' | 'partial' | string

const LABEL_MAP: Record<string, string> = {
  passed: 'Passed',
  failed: 'Failed',
  unknown: 'Unknown',
  warning: 'Warning',
  running: 'Running',
  recently_changed: 'Changed',
  stable: 'Stable',
  needs_review: 'Review',
  partial: 'Partial',
}

interface Props {
  status: Status
  label?: string
}

export function StatusBadge({ status, label }: Props) {
  const cls = STATUS_CLASS[status] ?? styles.unknown
  const text = label ?? LABEL_MAP[status] ?? status
  return <span className={`${styles.badge} ${cls}`}>{text}</span>
}

const STATUS_CLASS: Record<string, string> = {
  passed: styles.ok,
  stable: styles.ok,
  failed: styles.error,
  needs_review: styles.error,
  warning: styles.warning,
  recently_changed: styles.warning,
  partial: styles.warning,
  running: styles.accent,
  unknown: styles.unknown,
}
