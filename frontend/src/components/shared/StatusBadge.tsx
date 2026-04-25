import styles from './StatusBadge.module.css'
import { zhStatus } from '../../i18n'

type Status = 'passed' | 'failed' | 'unknown' | 'warning' | 'running' |
              'recently_changed' | 'stable' | 'needs_review' | 'partial' | string

const LABEL_MAP: Record<string, string> = {
  passed: '通过',
  failed: '失败',
  unknown: '未知',
  warning: '警告',
  running: '运行中',
  recently_changed: '最近变更',
  stable: '稳定',
  needs_review: '需复查',
  partial: '部分完成',
}

interface Props {
  status: Status
  label?: string
}

export function StatusBadge({ status, label }: Props) {
  const cls = STATUS_CLASS[status] ?? styles.unknown
  const text = label ?? LABEL_MAP[status] ?? zhStatus(status)
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
