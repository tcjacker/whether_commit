import { useState } from 'react'
import type { JourneyItem } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { EmptyState } from '../shared/EmptyState'
import { zhCount, zhCriticality } from '../../i18n'
import styles from './UserJourneysCard.module.css'

interface Props {
  journeys: JourneyItem[]
  loading: boolean
  highlightedNames: Set<string>
}

export function UserJourneysCard({ journeys, loading, highlightedNames }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const hasHighlight = highlightedNames.size > 0

  return (
    <CardShell title="用户旅程" subtitle={zhCount(journeys.length, '条路径')}>
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[1, 2].map(i => <SkeletonBlock key={i} height={52} />)}
        </div>
      ) : journeys.length === 0 ? (
        <EmptyState message="暂未推断出用户旅程。" />
      ) : (
        <ul className={styles.list}>
          {journeys.map(j => {
            const isOpen = expanded === j.name
            const dimmed = hasHighlight && !highlightedNames.has(j.name)
            return (
              <li key={j.name} className={`${styles.item} ${dimmed ? styles.dimmed : ''}`}>
                <button
                  className={`${styles.trigger} ${isOpen ? styles.open : ''}`}
                  onClick={() => setExpanded(isOpen ? null : j.name)}
                >
                  <span className={styles.chevron}>{isOpen ? '▾' : '▸'}</span>
                  <span className={styles.name}>{j.name}</span>
                  {j.criticality && (
                    <span className={`${styles.crit} ${styles[j.criticality] ?? ''}`}>
                      {zhCriticality(j.criticality)}
                    </span>
                  )}
                  {j.primary_actor && (
                    <span className={styles.actor}>{j.primary_actor}</span>
                  )}
                </button>
                {isOpen && (
                  <div className={styles.detail}>
                    {j.steps.length > 0 && (
                      <ol className={styles.steps}>
                        {j.steps.map((s, i) => (
                          <li key={i} className={styles.step}>
                            <span className={styles.stepNum}>{i + 1}</span>
                            <span>{s}</span>
                          </li>
                        ))}
                      </ol>
                    )}
                    {j.recent_impact && (
                      <p className={styles.impact}>⚡ {j.recent_impact}</p>
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
