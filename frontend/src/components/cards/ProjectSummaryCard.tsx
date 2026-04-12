import type { ProjectSummary } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import styles from './ProjectSummaryCard.module.css'

interface Props {
  summary: ProjectSummary | null
  loading: boolean
}

export function ProjectSummaryCard({ summary, loading }: Props) {
  return (
    <CardShell title="Project Summary">
      {loading || !summary ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <SkeletonBlock height={20} width="80%" />
          <SkeletonBlock height={14} lines={3} />
          <SkeletonBlock height={14} width="60%" />
        </div>
      ) : (
        <div className={styles.content}>
          <p className={styles.main}>{summary.what_this_app_seems_to_do || '—'}</p>

          {summary.core_flow && (
            <div className={styles.field}>
              <span className={styles.label}>Core flow</span>
              <span>{summary.core_flow}</span>
            </div>
          )}

          {summary.agent_reasoning?.technical_change_summary && (
            <div className={styles.field}>
              <span className={styles.label}>Recent AI focus</span>
              <span>{summary.agent_reasoning.technical_change_summary}</span>
            </div>
          )}

          {summary.agent_reasoning?.change_types?.length ? (
            <div className={styles.tags}>
              {summary.agent_reasoning.change_types.map(t => (
                <span key={t} className={styles.tag}>{t}</span>
              ))}
            </div>
          ) : null}

          {summary.technical_narrative && (
            <p className={styles.narrative}>{summary.technical_narrative}</p>
          )}

          {summary.agent_reasoning?.confidence && (
            <div className={styles.confidence}>
              Confidence: <strong>{summary.agent_reasoning.confidence}</strong>
            </div>
          )}
        </div>
      )}
    </CardShell>
  )
}
