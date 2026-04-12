import styles from './RiskBar.module.css'

interface Props {
  score: number
  showLabel?: boolean
}

export function RiskBar({ score, showLabel = true }: Props) {
  const pct = Math.round(Math.min(1, Math.max(0, score)) * 100)
  const cls = pct >= 70 ? styles.high : pct >= 40 ? styles.mid : styles.low

  return (
    <div className={styles.wrapper}>
      <div className={styles.track}>
        <div className={`${styles.fill} ${cls}`} style={{ width: `${pct}%` }} />
      </div>
      {showLabel && <span className={styles.label}>{pct}%</span>}
    </div>
  )
}
