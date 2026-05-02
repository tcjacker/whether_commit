import type { RecommendedTestCommand, TestCaseDetail, TestCommandRunResult, TestResultAnalysis } from '../../types/api'
import { t, zhStatus, type Language } from '../../i18n'
import styles from './TestResultPanel.module.css'
import { useState } from 'react'

function formatValue(value: string, language: Language) {
  return zhStatus(value, language)
}

function isAgentAnalysis(analysis: TestResultAnalysis | null | undefined) {
  return analysis?.source === 'generated' || analysis?.basis.includes('codex_agent')
}

function analysisHeading(analysis: TestResultAnalysis | null | undefined, language: Language) {
  return isAgentAnalysis(analysis) ? t(language, 'agentAnalysis') : t(language, 'ruleAnalysis')
}

function caseNameSourceLabel(source: string, language: Language) {
  return formatValue(source, language)
}

function statusEvidenceLabel({
  caseStatus,
  caseSource,
  commandStatus,
  language,
}: {
  caseStatus: string
  caseSource: string
  commandStatus: string
  language: Language
}) {
  if (caseSource === 'runner_output') return language === 'zh-CN' ? '来自运行器输出' : 'from runner output'
  if (caseSource === 'collect_only' && caseStatus === 'passed' && commandStatus === 'passed') {
    return language === 'zh-CN' ? '由命令 exit 0 推断' : 'inferred from command exit 0'
  }
  if (caseSource === 'collect_only') return language === 'zh-CN' ? '运行器输出未单独报告' : 'not independently reported by runner output'
  return language === 'zh-CN' ? '来自已存测试证据' : 'from stored test evidence'
}

function AnalysisDetails({ analysis, language }: { analysis: TestResultAnalysis, language: Language }) {
  const coveredCode = analysis.covered_code_analysis ?? []
  return (
    <section className={styles.block}>
      <h3>{analysisHeading(analysis, language)}</h3>
      <p>{analysis.summary}</p>
      <div className={styles.analysisMeta}>
        <small>{t(language, 'source')}: {formatValue(analysis.source, language)}</small>
      </div>
      {analysis.scenarios.length > 0 ? (
        <>
          <h4>{t(language, 'coveredScenarios')}</h4>
          <ul className={styles.scenarios}>
            {analysis.scenarios.map(scenario => (
              <li key={scenario.title}>{scenario.title}</li>
            ))}
          </ul>
        </>
      ) : null}
      {analysis.test_data.length > 0 ? (
        <>
          <h4>{t(language, 'testData')}</h4>
          <ul className={styles.scenarios}>
            {analysis.test_data.map(item => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}
      {coveredCode.length > 0 ? (
        <>
          <h4>{t(language, 'coveredChangedCode')}</h4>
          <ul className={styles.codeList}>
            {coveredCode.map(item => (
              <li key={`${item.path}-${item.hunk_id}-${item.symbol}`}>
                <strong>{item.path}</strong>
                {item.symbol ? <span>{item.symbol}</span> : null}
                <small>
                  {formatValue(item.relationship, language)} · {formatValue(item.evidence_grade, language)} · {item.hunk_id || (language === 'zh-CN' ? '无 hunk' : 'no hunk')}
                </small>
                {item.analysis ? <p>{item.analysis}</p> : null}
                {item.basis.length > 0 ? <small>{t(language, 'basis')}: {item.basis.map(item => formatValue(item, language)).join(' · ')}</small> : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {analysis.coverage_gaps.length > 0 ? (
        <>
          <h4>{t(language, 'coverageGaps')}</h4>
          <ul className={styles.gaps}>
            {analysis.coverage_gaps.map(gap => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </>
      ) : null}
      {analysis.basis.length > 0 ? (
        <>
          <h4>{t(language, 'evidenceBasis')}</h4>
          <p className={styles.basis}>{analysis.basis.map(item => formatValue(item, language)).join(' · ')}</p>
        </>
      ) : null}
    </section>
  )
}

function ExecutedCasesList({
  cases,
  commandStatus,
  language,
}: {
  cases: TestCommandRunResult['executed_cases']
  commandStatus: string
  language: Language
}) {
  if (cases.length === 0) {
    return <p>{t(language, 'noIndividualCases')}</p>
  }
  return (
    <ul className={styles.caseList}>
      {cases.map(testCase => (
        <li key={testCase.node_id}>
          <strong>{testCase.name}</strong>
          <span>{testCase.node_id}</span>
          <small>{t(language, 'status')}: {formatValue(testCase.status, language)}</small>
          <small>
            {t(language, 'statusEvidence')}:{' '}
            {statusEvidenceLabel({
              caseStatus: testCase.status,
              caseSource: testCase.source,
              commandStatus,
              language,
            })}
          </small>
          <small>{t(language, 'caseNameSource')}: {caseNameSourceLabel(testCase.source, language)}</small>
          {testCase.test_data.length > 0 ? <small>{t(language, 'data')}: {testCase.test_data.join(' · ')}</small> : null}
        </li>
      ))}
    </ul>
  )
}

export function TestResultPanel({
  detail,
  onRunCommand,
  onAnalyzeResult,
  language = 'en-US',
}: {
  detail: TestCaseDetail | null
  onRunCommand?: (command: RecommendedTestCommand) => Promise<TestCommandRunResult>
  onAnalyzeResult?: (runId: string) => Promise<TestResultAnalysis>
  language?: Language
}) {
  const result = detail?.test_results?.[0] ?? null
  const command = detail?.recommended_commands[0] ?? null
  const [modalOpen, setModalOpen] = useState(false)
  const [analysisModalOpen, setAnalysisModalOpen] = useState(false)
  const [running, setRunning] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [runAnalyzing, setRunAnalyzing] = useState(false)
  const [modalResult, setModalResult] = useState<TestCommandRunResult | null>(null)
  const [analysisResult, setAnalysisResult] = useState<TestResultAnalysis | null>(null)
  const [runAnalysisResult, setRunAnalysisResult] = useState<TestResultAnalysis | null>(null)
  const [modalError, setModalError] = useState<string | null>(null)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [runAnalysisError, setRunAnalysisError] = useState<string | null>(null)
  const [analysisRefreshMessage, setAnalysisRefreshMessage] = useState<string | null>(null)
  const modalAnalysis = modalResult && !runAnalyzing ? (runAnalysisResult ?? modalResult.analysis) : null

  const openRunConfirmation = () => {
    if (!command || !onRunCommand) return
    setModalOpen(true)
    setRunning(false)
    setRunAnalyzing(false)
    setModalResult(null)
    setRunAnalysisResult(null)
    setModalError(null)
    setRunAnalysisError(null)
  }

  const confirmAndRun = async () => {
    if (!command || !onRunCommand || running || runAnalyzing) return
    setRunning(true)
    setModalResult(null)
    setRunAnalysisResult(null)
    setModalError(null)
    setRunAnalysisError(null)
    try {
      const nextResult = await onRunCommand(command)
      setModalResult(nextResult)
      setRunning(false)
      if (!onAnalyzeResult) {
        setRunAnalysisError(t(language, 'agentAnalysisUnavailable'))
        return
      }
      setRunAnalyzing(true)
      try {
        setRunAnalysisResult(await onAnalyzeResult(nextResult.run_id))
      } catch (err) {
        setRunAnalysisError(String(err))
      } finally {
        setRunAnalyzing(false)
      }
    } catch (err) {
      setModalError(String(err))
      setRunning(false)
    }
  }

  const openAndAnalyze = async () => {
    setAnalysisModalOpen(true)
    setAnalysisResult(null)
    setAnalysisError(null)
    setAnalysisRefreshMessage(null)
    if (!result || !onAnalyzeResult) {
      setAnalysisError(t(language, 'noStoredTestResult'))
      return
    }
    setAnalyzing(true)
    try {
      await onAnalyzeResult(result.run_id)
      setAnalysisRefreshMessage(t(language, 'agentAnalysisRefreshed'))
      setAnalysisModalOpen(false)
    } catch (err) {
      setAnalysisError(String(err))
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <main className={styles.panel} aria-label="test-result">
      <header className={styles.header}>
        <div>
          <h2>{t(language, 'testResult')}</h2>
          <span>{detail ? detail.test_case.name : t(language, 'selectTestCase')}</span>
          {analysisRefreshMessage ? <small className={styles.statusNote}>{analysisRefreshMessage}</small> : null}
        </div>
        <div className={styles.actions}>
          {detail ? (
            <button type="button" onClick={openAndAnalyze} disabled={!onAnalyzeResult}>
              {t(language, 'agentAnalyze')}
            </button>
          ) : null}
          {command && onRunCommand ? (
            <button type="button" onClick={openRunConfirmation}>
              {t(language, 'rerun')}
            </button>
          ) : null}
        </div>
      </header>

      {!detail ? <p className={styles.empty}>{t(language, 'selectTestCaseResult')}</p> : null}
      {detail && !result ? (
        <section className={styles.emptyState}>
          <h3>{t(language, 'noTestExecutionEvidence')}</h3>
          <p>{language === 'zh-CN' ? '使用重新运行来执行推荐命令，然后在这里查看收集到的用例和分析。' : 'Use ReRun to execute the recommended command, then review the collected cases and analysis here.'}</p>
        </section>
      ) : null}
      {result ? (
        <>
          <section className={styles.summary}>
            <strong>{formatValue(result.status, language)}</strong>
            <span>exit {result.exit_code ?? 'unknown'}</span>
            <span>{result.duration_ms}ms</span>
            <span>{formatValue(result.source, language)}</span>
          </section>

          <AnalysisDetails analysis={result.analysis} language={language} />

          <section className={styles.block}>
            <h3>{t(language, 'executedCases')}</h3>
            <ExecutedCasesList cases={result.executed_cases} commandStatus={result.status} language={language} />
          </section>

          <section className={styles.block}>
            <h3>{t(language, 'rawOutput')}</h3>
            <pre>{result.stdout || result.stderr || t(language, 'noRawOutput')}</pre>
          </section>
        </>
      ) : null}
      {modalOpen ? (
        <div className={styles.modalBackdrop} role="presentation">
          <div className={styles.modal} role="dialog" aria-modal="true" aria-label="Confirm test rerun">
            <header>
              <h2>{modalResult ? t(language, 'testResultAnalysis') : t(language, 'confirmTestRerun')}</h2>
              <button type="button" onClick={() => setModalOpen(false)} disabled={running || runAnalyzing}>
                {t(language, 'close')}
              </button>
            </header>
            {!running && !runAnalyzing && !modalResult && !modalError ? (
              <section className={styles.block}>
                <h3>{t(language, 'command')}</h3>
                <p>{t(language, 'testRunCommandDescription')}</p>
                <code className={styles.commandPreview}>{command?.command}</code>
                {command?.reason ? <p>{command.reason}</p> : null}
                {command?.scope ? <small>{t(language, 'scope')}: {formatValue(command.scope, language)}</small> : null}
                <div className={styles.modalActions}>
                  <button type="button" onClick={() => setModalOpen(false)}>
                    {t(language, 'cancel')}
                  </button>
                  <button type="button" onClick={confirmAndRun}>
                    {t(language, 'runTest')}
                  </button>
                </div>
              </section>
            ) : null}
            {running ? <p>{t(language, 'runningTestCommand')}</p> : null}
            {runAnalyzing ? <p>{t(language, 'analyzingTestRun')}</p> : null}
            {modalError ? <p className={styles.error}>{modalError}</p> : null}
            {runAnalysisError ? <p className={styles.error}>{runAnalysisError}</p> : null}
            {modalResult ? (
              <>
                <section className={styles.summary}>
                  <strong>{formatValue(modalResult.status, language)}</strong>
                  <span>exit {modalResult.exit_code ?? 'unknown'}</span>
                  <span>{modalResult.duration_ms}ms</span>
                </section>
                {modalAnalysis ? <AnalysisDetails analysis={modalAnalysis} language={language} /> : null}
                <section className={styles.block}>
                  <h3>{t(language, 'executedCases')}</h3>
                  <ExecutedCasesList cases={modalResult.executed_cases} commandStatus={modalResult.status} language={language} />
                </section>
                <section className={styles.block}>
                  <h3>{t(language, 'rawOutput')}</h3>
                  <pre>{modalResult.stdout || modalResult.stderr || t(language, 'noRawOutput')}</pre>
                </section>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
      {analysisModalOpen ? (
        <div className={styles.modalBackdrop} role="presentation">
          <div className={styles.modal} role="dialog" aria-modal="true" aria-label="Agent test result analysis">
            <header>
              <h2>{t(language, 'agentTestResultAnalysis')}</h2>
              <button type="button" onClick={() => setAnalysisModalOpen(false)}>{t(language, 'close')}</button>
            </header>
            {analyzing ? <p>{t(language, 'analyzingStoredTestResult')}</p> : null}
            {analysisError ? <p className={styles.error}>{analysisError}</p> : null}
            {analysisResult ? (
              <>
                <AnalysisDetails analysis={analysisResult} language={language} />
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </main>
  )
}
