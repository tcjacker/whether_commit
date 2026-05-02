import { useState } from 'react'
import type { RecommendedTestCommand, TestCaseDetail, TestCommandRunResult } from '../../types/api'
import { t, zhStatus, type Language } from '../../i18n'
import styles from './TestEvidencePanel.module.css'

function formatValue(value: string, language: Language) {
  return zhStatus(value, language)
}

function MetaList({ items }: { items: string[] }) {
  if (items.length === 0) return null
  return (
    <ul className={styles.metaList}>
      {items.map(item => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}

export function TestEvidencePanel({
  detail,
  onRunCommand,
  language = 'en-US',
}: {
  detail: TestCaseDetail | null
  onRunCommand?: (command: RecommendedTestCommand) => Promise<TestCommandRunResult>
  language?: Language
}) {
  const [pendingCommand, setPendingCommand] = useState<RecommendedTestCommand | null>(null)
  const [runningCommandId, setRunningCommandId] = useState<string | null>(null)
  const [runResult, setRunResult] = useState<TestCommandRunResult | null>(null)
  const [runError, setRunError] = useState<string | null>(null)

  if (!detail) {
    return (
      <aside className={styles.panel} aria-label="test-evidence">
        <p className={styles.empty}>{t(language, 'selectTestCaseEvidence')}</p>
      </aside>
    )
  }

  const testCase = detail.test_case
  const intentBasis = testCase.intent_summary.basis

  const confirmRun = async () => {
    if (!pendingCommand || !onRunCommand) return
    setRunError(null)
    setRunResult(null)
    setRunningCommandId(pendingCommand.command_id)
    try {
      const result = await onRunCommand(pendingCommand)
      setRunResult(result)
    } catch (err) {
      setRunError(String(err))
    } finally {
      setRunningCommandId(null)
      setPendingCommand(null)
    }
  }

  return (
    <aside className={styles.panel} aria-label="test-evidence">
      <div className={styles.signalPanel}>
        <dl>
          <div>
            <dt>{t(language, 'status')}</dt>
            <dd>{formatValue(testCase.status, language)}</dd>
          </div>
          <div>
            <dt>{t(language, 'evidence')}</dt>
            <dd>{formatValue(testCase.evidence_grade, language)}</dd>
          </div>
          <div>
            <dt>{t(language, 'confidence')}</dt>
            <dd>{formatValue(testCase.extraction_confidence, language)}</dd>
          </div>
          <div>
            <dt>{language === 'zh-CN' ? '最近运行' : 'Last run'}</dt>
            <dd>{formatValue(testCase.last_status, language)}</dd>
          </div>
        </dl>
      </div>

      <section>
        <h2>{t(language, 'testIntent')}</h2>
        <p>{testCase.intent_summary.text}</p>
        <p className={styles.meta}>
          {t(language, 'source')}: <span>{formatValue(testCase.intent_summary.source, language)}</span>
        </p>
        <MetaList items={intentBasis} />
      </section>

      <section>
        <h2>{t(language, 'coveredScenarios')}</h2>
        {detail.covered_scenarios.length === 0 ? (
          <p>{t(language, 'noCoveredScenarios')}</p>
        ) : (
          <ul className={styles.evidenceList}>
            {detail.covered_scenarios.map(scenario => (
              <li key={scenario.title}>
                <span>{scenario.title}</span>
                <small>
                  {formatValue(scenario.source, language)} · {scenario.basis.join(', ')}
                </small>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2>{t(language, 'coveredChangedCode')}</h2>
        {detail.covered_changes.length === 0 ? (
          <p>{t(language, 'noCoveredChangedCode')}</p>
        ) : (
          <ul className={styles.evidenceList}>
            {detail.covered_changes.map(change => (
              <li key={`${change.path}-${change.hunk_id}-${change.symbol}`}>
                <span>{change.path}</span>
                <strong>{change.symbol}</strong>
                <small>
                  <span>{formatValue(change.relationship, language)}</span> · {formatValue(change.evidence_grade, language)} · {change.hunk_id}
                </small>
                <MetaList items={change.basis} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2>{t(language, 'agentClaims')}</h2>
        {detail.related_agent_claims.length === 0 ? (
          <p>{t(language, 'noRelatedAgentClaims')}</p>
        ) : (
          <ul className={styles.evidenceList}>
            {detail.related_agent_claims.map(claim => (
              <li key={claim.claim_id}>
                <span>{claim.text}</span>
                <small>
                  {formatValue(claim.type, language)} · {claim.source} · {formatValue(claim.confidence, language)}
                </small>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2>{t(language, 'recommendedCommands')}</h2>
        {detail.recommended_commands.length === 0 ? (
          <p>{t(language, 'noRecommendedCommand')}</p>
        ) : (
          <ul className={styles.commandList}>
            {detail.recommended_commands.map(command => (
              <li key={command.command_id}>
                <div className={styles.commandRow}>
                  <code>{command.command}</code>
                  {onRunCommand ? (
                    <button
                      type="button"
                      disabled={runningCommandId === command.command_id}
                      onClick={() => setPendingCommand(command)}
                    >
                      {runningCommandId === command.command_id ? t(language, 'running') : t(language, 'rerun')}
                    </button>
                  ) : null}
                </div>
                <small>
                  {command.reason} · {formatValue(command.scope, language)} · {formatValue(command.status, language)}
                </small>
              </li>
            ))}
          </ul>
        )}
        {runError ? <p className={styles.runError}>{runError}</p> : null}
        {runResult ? (
          <div className={styles.runResult}>
            <strong>
              {formatValue(runResult.status, language)} · exit {runResult.exit_code ?? 'timeout'} · {runResult.duration_ms}ms
            </strong>
            {runResult.stdout ? <pre>{runResult.stdout}</pre> : null}
            {runResult.stderr ? <pre>{runResult.stderr}</pre> : null}
          </div>
        ) : null}
      </section>

      <section>
        <h2>{t(language, 'unknowns')}</h2>
        {detail.unknowns.length === 0 ? (
          <p>{t(language, 'noUnknownsRecorded')}</p>
        ) : (
          <ul className={styles.metaList}>
            {detail.unknowns.map(unknown => (
              <li key={unknown}>{unknown}</li>
            ))}
          </ul>
        )}
      </section>
      {pendingCommand ? (
        <div className={styles.modalBackdrop} role="presentation">
          <div className={styles.modal} role="dialog" aria-modal="true" aria-label="Confirm test command run">
            <h2>{t(language, 'rerunRecommendedTest')}</h2>
            <p>{t(language, 'testRunRecommendedDescription')}</p>
            <code>{pendingCommand.command}</code>
            <div className={styles.modalActions}>
              <button type="button" onClick={() => setPendingCommand(null)}>
                {t(language, 'cancel')}
              </button>
              <button type="button" onClick={confirmRun}>
                {t(language, 'rerun')}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </aside>
  )
}
