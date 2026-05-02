import type { ChangedFileDetail } from '../../types/api'
import { formatValue, t, type Language } from '../../i18n'
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

function assessmentLabel(detail: ChangedFileDetail, language: Language) {
  if (detail.file_assessment.generated_by === 'codex_agent' && detail.file_assessment.agent_status === 'accepted') {
    return t(language, 'agentAssessmentAccepted')
  }
  if (detail.file_assessment.agent_status === 'failed') return t(language, 'ruleFallback')
  if (detail.file_assessment.agent_status === 'fallback') return t(language, 'ruleFallback')
  return t(language, 'ruleFallback')
}

function dedupeHunkFactChecks(hunkItems: NonNullable<ChangedFileDetail['hunk_review_items']>) {
  const checks = new Map<string, { priority: number; reasons: string[]; count: number }>()

  for (const item of hunkItems) {
    const key = `${item.priority}:${item.reasons.join('\n')}:${item.fact_basis.join('\n')}`
    const existing = checks.get(key)
    if (existing) {
      existing.count += 1
    } else {
      checks.set(key, { priority: item.priority, reasons: item.reasons, count: 1 })
    }
  }

  return [...checks.values()].sort((a, b) => b.priority - a.priority)
}

function titleCase(value: string) {
  if (!value) return ''
  return value[0].toUpperCase() + value.slice(1)
}

function provenanceKind(source: string) {
  if (source.includes('apply_patch')) return 'apply_patch changed this file'
  if (source === 'codex_command') return 'command touched this file'
  if (source.startsWith('message:')) return 'message mentioned this file'
  return `${source} linked this file`
}

function isAgentProvenance(ref: NonNullable<ChangedFileDetail['provenance_refs']>[number]) {
  return ref.source !== 'git_diff'
}

function provenanceMeta(ref: NonNullable<ChangedFileDetail['provenance_refs']>[number]) {
  const parts: string[] = []
  if (ref.message_ref) parts.push(`message ${ref.message_ref}`)
  if (ref.tool_call_ref) parts.push(`tool call ${ref.tool_call_ref}`)
  if (ref.command) parts.push(ref.command)
  if (ref.hunk_id) parts.push(ref.hunk_id)
  if (ref.session_id) parts.push(`session ${ref.session_id}`)
  return parts.join(' · ')
}

export function FileEvidencePanel({
  detail,
  onRunAgent,
  running = false,
  language = 'en-US',
}: {
  detail: ChangedFileDetail | null
  onRunAgent?: () => void
  running?: boolean
  language?: Language
}) {
  if (!detail) return <aside className={styles.panel}>{t(language, 'noFileSelected')}</aside>
  const sources = detail.related_agent_records
    .map(record => `${record.source} (${record.capture_level})`)
    .join(', ') || detail.file.agent_sources.join(', ') || 'unknown'
  const testPreview = detail.related_tests.slice(0, 3)
  const claims = detail.agent_claims ?? []
  const mismatches = detail.mismatches ?? []
  const provenanceRefs = detail.provenance_refs ?? []
  const agentProvenanceRefs = provenanceRefs.filter(isAgentProvenance)
  const hunkItems = detail.hunk_review_items ?? []
  const factChecks = dedupeHunkFactChecks(hunkItems)
  const weakestGrade = detail.file.weakest_test_evidence_grade ?? detail.related_tests[0]?.evidence_grade ?? 'unknown'

  const isRunning = running || detail.file_assessment.agent_status === 'running'
  const canRunAgent = !isRunning && detail.file_assessment.generated_by !== 'codex_agent'
  return (
    <aside className={styles.panel} aria-label="file-evidence">
      <div className={styles.signalPanel}>
        <div>
          <strong>{t(language, 'reviewSignals')}</strong>
          <span>{t(language, 'reviewSignalsDescription')}</span>
        </div>
        <dl>
          <div>
            <dt>Claim</dt>
            <dd>{claims[0]?.type ?? 'none'}</dd>
          </div>
          <div>
            <dt>{t(language, 'mismatch')}</dt>
            <dd>{mismatches.length}</dd>
          </div>
          <div>
            <dt>{t(language, 'evidence')}</dt>
            <dd>{weakestGrade}</dd>
          </div>
          <div>
            <dt>{t(language, 'hunk')}</dt>
            <dd>{hunkItems[0] ? `P${hunkItems[0].priority}` : 'none'}</dd>
          </div>
          <div>
            <dt>{t(language, 'provenance')}</dt>
            <dd>{provenanceRefs[0]?.confidence ?? 'none'}</dd>
          </div>
        </dl>
      </div>
      <div className={detail.file_assessment.generated_by === 'codex_agent' ? styles.agentBadge : styles.fallbackBadge}>
        <strong>{isRunning ? t(language, 'agentAssessmentRunning') : assessmentLabel(detail, language)}</strong>
        <span>{t(language, 'confidence')}: {detail.file_assessment.confidence}</span>
        {isRunning && <span className={styles.spinner} aria-label="agent-running" />}
        {canRunAgent && onRunAgent && (
          <button className={styles.runButton} onClick={onRunAgent}>{t(language, 'runCodexAssessment')}</button>
        )}
      </div>
      <section>
        <h2>{t(language, 'verdict')}</h2>
        <p>{t(language, 'risk')}: {detail.file.risk_level}</p>
        <p>{t(language, 'coverage')}: {detail.file.coverage_status}</p>
        <p>{t(language, 'evidenceGrade')}: {weakestGrade}</p>
        <EvidenceText text={detail.file_assessment.recommended_action} />
      </section>
      <section>
        <h2>{t(language, 'agentClaims')}</h2>
        <EvidenceText text={detail.file_assessment.why_changed} />
        <p className={styles.meta}>{t(language, 'sources')}: {sources}</p>
        {detail.file_assessment.evidence_refs.length > 0 && (
          <p className={styles.meta}>{t(language, 'evidence')}: {detail.file_assessment.evidence_refs.join(', ')}</p>
        )}
        {claims.length > 0 && (
          <ul className={styles.evidenceList}>
            {claims.map(claim => (
              <li key={claim.claim_id}>
                <span>{claim.text}</span>
                <small>{claim.type} · {claim.source} · {claim.confidence}</small>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h2>{t(language, 'factChecks')}</h2>
        <EvidenceText text={detail.file_assessment.impact_summary} />
        <p className={styles.meta}>{t(language, 'symbols')}: {detail.changed_symbols.length}</p>
        {factChecks.length > 0 && (
          <ul className={styles.evidenceList}>
            {factChecks.map(item => (
              <li key={`${item.priority}-${item.reasons.join('|')}`}>
                <span>{t(language, 'priority')} {item.priority}</span>
                <small>
                  {item.reasons.join(' · ')}
                  {item.count > 1 ? ` · ${item.count} hunks` : ''}
                </small>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h2>{t(language, 'mismatches')}</h2>
        {mismatches.length === 0 ? (
          <p>{t(language, 'noClaimFactMismatch')}</p>
        ) : (
          <ul className={styles.evidenceList}>
            {mismatches.map(mismatch => (
              <li key={mismatch.mismatch_id}>
                <span>{mismatch.kind}</span>
                <small>{formatValue(mismatch.severity, language)} · {mismatch.explanation}</small>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h2>{t(language, 'testEvidence')}</h2>
        <EvidenceText text={detail.file_assessment.test_summary} />
        <p className={styles.meta}>{t(language, 'relatedTests')}: {detail.related_tests.length}</p>
        {testPreview.length > 0 && (
          <ul className={styles.evidenceList}>
            {testPreview.map(test => (
              <li key={test.test_id}>
                <span>{test.path}</span>
                <small>{test.evidence_grade ?? test.evidence} · {test.relationship} · {test.confidence} · {test.last_status}</small>
              </li>
            ))}
          </ul>
        )}
        {detail.file_assessment.unknowns.length > 0 && (
          <p className={styles.meta}>{t(language, 'unknowns')}: {detail.file_assessment.unknowns.join(', ')}</p>
        )}
      </section>
      <section>
        <h2>{t(language, 'provenance')}</h2>
        {agentProvenanceRefs.length === 0 ? (
          <>
            <p>{t(language, 'noAgentProvenance')}</p>
            {provenanceRefs.length > 0 && (
              <p className={styles.meta}>{t(language, 'onlyGitDiffEvidence')}</p>
            )}
          </>
        ) : (
          <ul className={styles.evidenceList}>
            {agentProvenanceRefs.map(ref => (
              <li key={`${ref.source}-${ref.session_id}-${ref.message_ref}-${ref.tool_call_ref}-${ref.hunk_id}`}>
                <span>{titleCase(ref.confidence)} · {provenanceKind(ref.source)}</span>
                <small>{provenanceMeta(ref)}</small>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  )
}
