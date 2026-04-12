import type { CapabilityItem } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { StatusBadge } from '../shared/StatusBadge'
import { EmptyState } from '../shared/EmptyState'
import styles from './CapabilityMapCard.module.css'

interface Props {
  capabilities: CapabilityItem[]
  loading: boolean
  highlightedKeys: Set<string>
  selectedKey: string | null
  onSelect: (key: string | null) => void
}

export function CapabilityMapCard({ capabilities, loading, highlightedKeys, selectedKey, onSelect }: Props) {
  const hasHighlight = highlightedKeys.size > 0

  return (
    <CardShell title="Capability Map" subtitle={`${capabilities.length} capabilities`}>
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[1,2,3].map(i => <SkeletonBlock key={i} height={44} />)}
        </div>
      ) : capabilities.length === 0 ? (
        <EmptyState message="No capabilities detected yet. Run a rebuild to analyze the codebase." />
      ) : (
        <ul className={styles.list}>
          {capabilities.map(cap => {
            const isSelected = selectedKey === cap.capability_key
            const dimmed = hasHighlight && !highlightedKeys.has(cap.capability_key)
            return (
              <li
                key={cap.capability_key}
                className={`${styles.item} ${isSelected ? styles.selected : ''} ${dimmed ? styles.dimmed : ''}`}
                onClick={() => onSelect(isSelected ? null : cap.capability_key)}
              >
                <div className={styles.row}>
                  <span className={styles.name}>{cap.name}</span>
                  <StatusBadge status={cap.status} />
                </div>
                <div className={styles.meta}>
                  {cap.linked_routes.length > 0 && (
                    <span className={styles.routes}>
                      {cap.linked_routes.slice(0, 2).join(', ')}
                      {cap.linked_routes.length > 2 && ` +${cap.linked_routes.length - 2}`}
                    </span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </CardShell>
  )
}
