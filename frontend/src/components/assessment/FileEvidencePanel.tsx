import type { ChangedFileDetail } from '../../types/api'
import styles from './FileEvidencePanel.module.css'

export function FileEvidencePanel({ detail }: { detail: ChangedFileDetail | null }) {
  if (!detail) return <aside className={styles.panel}>No file selected.</aside>
  return (
    <aside className={styles.panel} aria-label="file-evidence">
      <section>
        <h2>Verdict</h2>
        <p>Risk: {detail.file.risk_level}</p>
        <p>Coverage: {detail.file.coverage_status}</p>
        <p>{detail.file_assessment.recommended_action}</p>
      </section>
      <section>
        <h2>Why</h2>
        <p>{detail.file_assessment.why_changed}</p>
        <p>Sources: {detail.file.agent_sources.join(', ') || 'unknown'}</p>
      </section>
      <section>
        <h2>Impact</h2>
        <p>{detail.file_assessment.impact_summary}</p>
        <p>Symbols: {detail.changed_symbols.length}</p>
      </section>
      <section>
        <h2>Tests</h2>
        <p>{detail.file_assessment.test_summary}</p>
        <p>Related tests: {detail.related_tests.length}</p>
      </section>
    </aside>
  )
}
