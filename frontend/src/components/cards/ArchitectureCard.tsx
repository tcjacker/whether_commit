import type { ArchitectureOverview } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { EmptyState } from '../shared/EmptyState'
import { ArchitectureDiagram } from '../architecture/ArchitectureDiagram'
import { zhNodeType } from '../../i18n'
import styles from './ArchitectureCard.module.css'

interface Props {
  architecture: ArchitectureOverview
  loading: boolean
  highlightedNodeIds: Set<string>
}

export function ArchitectureCard({ architecture, loading, highlightedNodeIds }: Props) {
  const nodeCount = architecture.nodes.length
  const edgeCount = architecture.edges.length

  return (
    <CardShell
      title="系统架构"
      subtitle={nodeCount ? `${nodeCount} 个节点 · ${edgeCount} 条边` : undefined}
    >
      {loading ? (
        <SkeletonBlock height={300} />
      ) : nodeCount === 0 ? (
        <EmptyState message="暂未生成架构图。" />
      ) : (
        <div className={styles.wrap}>
          <ArchitectureDiagram
            nodes={architecture.nodes}
            edges={architecture.edges}
            highlightedNodeIds={highlightedNodeIds}
            height={320}
          />
          <div className={styles.legend}>
            {['service', 'repository', 'external integration', 'config'].map(t => (
              <span key={t} className={styles.legendItem}>
                <span className={styles.dot} style={{ background: TYPE_SAMPLE[t] }} />
                {zhNodeType(t)}
              </span>
            ))}
          </div>
        </div>
      )}
    </CardShell>
  )
}

const TYPE_SAMPLE: Record<string, string> = {
  service: '#7c3aed',
  repository: '#059669',
  'external integration': '#64748b',
  config: '#475569',
}
