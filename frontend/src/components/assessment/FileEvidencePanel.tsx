import type { ChangedFileDetail } from '../../types/api'
import styles from './FileEvidencePanel.module.css'

function EvidenceText({ text }: { text: string }) {
  return (
    <>
      {text.split(' | ').map(part => (
        <p key={part}>{part}</p>
      ))}
    </>
  )
}

function assessmentLabel(detail: ChangedFileDetail) {
  if (detail.file_assessment.generated_by === 'codex_agent' && detail.file_assessment.agent_status === 'accepted') {
    return 'Agent assessment · Codex'
  }
  if (detail.file_assessment.agent_status === 'failed') return 'Rule-based fallback'
  if (detail.file_assessment.agent_status === 'fallback') return 'Rule-based fallback'
  return 'Rule-based fallback'
}

export function FileEvidencePanel({
  detail,
  onRunAgent,
  running = false,
}: {
  detail: ChangedFileDetail | null
  onRunAgent?: () => void
  running?: boolean
}) {
  if (!detail) return <aside className={styles.panel}>No file selected.</aside>
  const sources = detail.related_agent_records
    .map(record => `${record.source} (${record.capture_level})`)
    .join(', ') || detail.file.agent_sources.join(', ') || 'unknown'
  const testPreview = detail.related_tests.slice(0, 3)

  const isRunning = running || detail.file_assessment.agent_status === 'running'
  const canRunAgent = !isRunning && detail.file_assessment.generated_by !== 'codex_agent'
  return (
    <aside className={styles.panel} aria-label="file-evidence">
      <div className={detail.file_assessment.generated_by === 'codex_agent' ? styles.agentBadge : styles.fallbackBadge}>
        <strong>{isRunning ? 'Agent assessment running · Codex' : assessmentLabel(detail)}</strong>
        <span>confidence: {detail.file_assessment.confidence}</span>
        {isRunning && <span className={styles.spinner} aria-label="agent-running" />}
        {canRunAgent && onRunAgent && (
          <button className={styles.runButton} onClick={onRunAgent}>Run Codex Assessment</button>
        )}
      </div>
      <section>
        <h2>Verdict</h2>
        <p>Risk: {detail.file.risk_level}</p>
        <p>Coverage: {detail.file.coverage_status}</p>
        <EvidenceText text={detail.file_assessment.recommended_action} />
      </section>
      <section>
        <h2>Why</h2>
        <EvidenceText text={detail.file_assessment.why_changed} />
        <p className={styles.meta}>Sources: {sources}</p>
        {detail.file_assessment.evidence_refs.length > 0 && (
          <p className={styles.meta}>Evidence: {detail.file_assessment.evidence_refs.join(', ')}</p>
        )}
      </section>
      <section>
        <h2>Impact</h2>
        <EvidenceText text={detail.file_assessment.impact_summary} />
        <p className={styles.meta}>Symbols: {detail.changed_symbols.length}</p>
      </section>
      <section>
        <h2>Tests</h2>
        <EvidenceText text={detail.file_assessment.test_summary} />
        <p className={styles.meta}>Related tests: {detail.related_tests.length}</p>
        {testPreview.length > 0 && (
          <ul className={styles.evidenceList}>
            {testPreview.map(test => (
              <li key={test.test_id}>
                <span>{test.path}</span>
                <small>{test.relationship} · {test.confidence} · {test.last_status}</small>
              </li>
            ))}
          </ul>
        )}
        {detail.file_assessment.unknowns.length > 0 && (
          <p className={styles.meta}>Unknowns: {detail.file_assessment.unknowns.join(', ')}</p>
        )}
      </section>
    </aside>
  )
}
