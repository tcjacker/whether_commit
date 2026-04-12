import type { RecentAIChange } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { RiskBar } from '../shared/RiskBar'
import { EmptyState } from '../shared/EmptyState'
import styles from './AIChangesCard.module.css'

interface Props {
  changes: RecentAIChange[]
  loading: boolean
  highlightedIds: Set<string>
  selectedId: string | null
  onSelect: (id: string | null) => void
}

export function AIChangesCard({ changes, loading, highlightedIds, selectedId, onSelect }: Props) {
  const hasHighlight = highlightedIds.size > 0

  return (
    <CardShell title="Recent AI Changes" subtitle={changes.length ? `${changes.length} change sets` : undefined}>
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[1, 2].map(i => <SkeletonBlock key={i} height={72} />)}
        </div>
      ) : changes.length === 0 ? (
        <EmptyState message="No pending changes detected in the working tree." />
      ) : (
        <ul className={styles.list}>
          {changes.map(c => {
            const isSelected = selectedId === c.change_id
            const dimmed = hasHighlight && !highlightedIds.has(c.change_id)

            // Derive a 0–1 risk score from risk_factors count if no explicit score
            const riskScore = c.risk_factors.length > 0
              ? Math.min(1, c.risk_factors.length / 5)
              : 0.1

            return (
              <li
                key={c.change_id}
                className={`${styles.item} ${isSelected ? styles.selected : ''} ${dimmed ? styles.dimmed : ''}`}
                onClick={() => onSelect(isSelected ? null : c.change_id)}
              >
                <div className={styles.header}>
                  <span className={styles.title}>{c.change_title}</span>
                  <span className={`${styles.confidence} ${styles[c.confidence] ?? ''}`}>
                    {c.confidence}
                  </span>
                </div>

                {c.summary && <p className={styles.summary}>{c.summary}</p>}

                {c.change_types.length > 0 && (
                  <div className={styles.tags}>
                    {c.change_types.map(t => (
                      <span key={t} className={styles.tag}>{t.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                )}

                <div className={styles.footer}>
                  <span className={styles.files}>
                    {c.changed_files.length} file{c.changed_files.length !== 1 ? 's' : ''}
                  </span>
                  <RiskBar score={riskScore} />
                </div>

                {isSelected && c.risk_factors.length > 0 && (
                  <div className={styles.detail}>
                    <p className={styles.detailLabel}>Risk factors</p>
                    <ul className={styles.riskList}>
                      {c.risk_factors.map((r, i) => (
                        <li key={i}>⚠ {r}</li>
                      ))}
                    </ul>
                    {c.review_recommendations.length > 0 && (
                      <>
                        <p className={styles.detailLabel} style={{ marginTop: 8 }}>Recommendations</p>
                        <ul className={styles.riskList}>
                          {c.review_recommendations.map((r, i) => (
                            <li key={i}>→ {r}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </CardShell>
  )
}
