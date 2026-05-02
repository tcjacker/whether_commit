import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchLatestAssessment } from '../api/assessments'
import {
  fetchVerificationRun,
  fetchCurrentSnapshot,
  rebuildPrecommitReview,
  runVerificationCommand,
  updateHunkReviewState,
  updateSignalReviewState,
} from '../api/precommitReview'
import { AssessmentSummaryBar } from '../components/assessment/AssessmentSummaryBar'
import { RebuildButton } from '../components/rebuild/RebuildButton'
import { RebuildProgress } from '../components/rebuild/RebuildProgress'
import { useAssessmentRebuild } from '../hooks/useAssessmentRebuild'
import { readStoredLanguage, storeLanguage, type Language } from '../i18n'
import type { AssessmentManifest, JobState, PrecommitFile, PrecommitHunk, PrecommitSnapshot, VerificationRun } from '../types/api'
import { isTestFile } from '../utils/testFiles'
import styles from './PrecommitReviewPage.module.css'

type ActiveModule = 'review' | 'tests'

const COPY: Record<Language, Record<string, string>> = {
  'en-US': {
    acceptRisk: 'Accept risk',
    additions: 'additions',
    aligned: 'aligned',
    deletions: 'deletions',
    evidence: 'Evidence',
    highRiskQueue: 'Unresolved Review Queue',
    hunkStatus: 'Hunk status',
    language: 'Language',
    loading: 'Loading pre-commit review...',
    markHunkReviewed: 'Mark hunk reviewed',
    misaligned: 'misaligned',
    noHunks: 'No hunks to review.',
    noPending: 'no pending staged changes',
    noSelection: 'No staged file selected',
    noStagedFiles: 'No staged files',
    noUnresolved: 'No unresolved review items.',
    rebuild: 'Rebuild',
    review: 'Review',
    risk: 'Risk',
    runVerification: 'Run verification',
    signals: 'Signals',
    simplifiedChinese: '简体中文',
    english: 'English',
    stagedFiles: 'Staged Files',
    staleSnapshot: 'stale snapshot',
    testFiles: 'Test Files',
    tests: 'Tests',
    verification: 'Verification',
    workspaceChangedOutsideTarget: 'workspace changed outside target',
  },
  'zh-CN': {
    acceptRisk: '接受风险',
    additions: '新增',
    aligned: '已对齐',
    deletions: '删除',
    evidence: '证据',
    highRiskQueue: '未解决审查队列',
    hunkStatus: 'Hunk 状态',
    language: '语言',
    loading: '正在加载提交前审查...',
    markHunkReviewed: '标记 hunk 已审',
    misaligned: '未对齐',
    noHunks: '没有需要审查的 hunk。',
    noPending: '没有暂存变更',
    noSelection: '未选择暂存文件',
    noStagedFiles: '没有暂存文件',
    noUnresolved: '没有未解决审查项。',
    rebuild: '重建',
    review: '审查',
    risk: '风险',
    runVerification: '运行验证',
    signals: '信号',
    simplifiedChinese: '简体中文',
    english: 'English',
    stagedFiles: '暂存文件',
    staleSnapshot: '快照已过期',
    testFiles: '测试文件',
    tests: '测试',
    verification: '验证',
    workspaceChangedOutsideTarget: '工作区存在目标外变更',
  },
}

function t(language: Language, key: string) {
  return COPY[language][key] ?? key
}

function getWorkspacePath() {
  return new URLSearchParams(window.location.search).get('workspace_path') ?? ''
}

function getRepoKey() {
  return new URLSearchParams(window.location.search).get('repo_key') ?? 'divide_prd_to_ui'
}

function decisionClass(decision: string) {
  if (decision === 'no_known_blockers') return styles.good
  if (decision === 'not_recommended') return styles.bad
  return styles.review
}

function decisionLabel(decision: string) {
  return decision.replaceAll('_', ' ')
}

function translatedDecision(decision: string, language: Language) {
  if (language === 'en-US') return decisionLabel(decision)
  if (decision === 'no_known_blockers') return '未发现阻断项'
  if (decision === 'needs_review') return '需要审查'
  if (decision === 'not_recommended') return '不建议提交'
  return decisionLabel(decision)
}

function linePrefix(type: string) {
  if (type === 'add') return '+'
  if (type === 'remove') return '-'
  return ' '
}

function assessmentFallbackMessage(error: string | null, language: Language) {
  if (!error) {
    return language === 'zh-CN'
      ? '正在加载提交分析。'
      : 'Loading commit assessment.'
  }
  if (error.includes('ASSESSMENT_NOT_READY')) {
    return language === 'zh-CN'
      ? '提交分析还未生成。请先触发重建。'
      : 'Commit assessment is not ready. Please trigger a rebuild first.'
  }
  return language === 'zh-CN'
    ? '提交分析暂不可用。可以先触发重建。'
    : 'Commit assessment is unavailable. You can trigger a rebuild.'
}

export function PrecommitReviewPage() {
  const workspacePath = getWorkspacePath()
  const repoKey = getRepoKey()
  const [assessment, setAssessment] = useState<AssessmentManifest | null>(null)
  const [snapshot, setSnapshot] = useState<PrecommitSnapshot | null>(null)
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [activeModule, setActiveModule] = useState<ActiveModule>('review')
  const [language, setLanguage] = useState<Language>(() => readStoredLanguage())
  const [command, setCommand] = useState('')
  const [verificationRun, setVerificationRun] = useState<VerificationRun | null>(null)
  const [evidenceRun, setEvidenceRun] = useState<VerificationRun | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [snapshotNotReady, setSnapshotNotReady] = useState(false)
  const [assessmentError, setAssessmentError] = useState<string | null>(null)

  const loadAssessment = useCallback(() => fetchLatestAssessment(repoKey, workspacePath)
    .then(data => {
      setAssessment(data)
      setAssessmentError(null)
      return data
    }), [repoKey, workspacePath])

  const {
    rebuild: rebuildAssessment,
    isRebuilding: isAssessmentRebuilding,
    job: assessmentJob,
    rebuildError: assessmentRebuildError,
  } = useAssessmentRebuild(repoKey, workspacePath, loadAssessment)

  useEffect(() => {
    fetchCurrentSnapshot(workspacePath)
      .then(data => {
        setSnapshot(data)
        setSnapshotNotReady(false)
        setSelectedFileId(data.files[0]?.file_id ?? null)
      })
      .catch(err => {
        const message = String(err)
        if (message.includes('PRECOMMIT_REVIEW_NOT_READY')) {
          setSnapshotNotReady(true)
          return
        }
        setError(message)
      })
  }, [workspacePath])

  useEffect(() => {
    loadAssessment()
      .catch(err => setAssessmentError(String(err)))
  }, [loadAssessment])

  const selectedFile = useMemo(
    () => snapshot?.files.find(file => file.file_id === selectedFileId) ?? null,
    [snapshot, selectedFileId],
  )
  const visibleFiles = useMemo(() => {
    const files = snapshot?.files ?? []
    return activeModule === 'tests'
      ? files.filter(file => isTestFile(file.path))
      : files.filter(file => !isTestFile(file.path))
  }, [snapshot, activeModule])
  const selectedHunks = useMemo(
    () => snapshot?.hunks.filter(hunk => hunk.file_id === selectedFileId) ?? [],
    [snapshot, selectedFileId],
  )

  const setSnapshotAndSelection = (next: PrecommitSnapshot) => {
    setSnapshot(next)
    setSelectedFileId(current => current ?? next.files.find(file => !isTestFile(file.path))?.file_id ?? next.files[0]?.file_id ?? null)
  }

  useEffect(() => {
    if (!snapshot) return
    const nextFiles = activeModule === 'tests'
      ? snapshot.files.filter(file => isTestFile(file.path))
      : snapshot.files.filter(file => !isTestFile(file.path))
    setSelectedFileId(current => nextFiles.some(file => file.file_id === current) ? current : nextFiles[0]?.file_id ?? null)
  }, [snapshot, activeModule])

  const handleHunkReviewed = (hunk: PrecommitHunk) => {
    updateHunkReviewState(workspacePath, hunk.hunk_id, 'reviewed')
      .then(setSnapshotAndSelection)
      .catch(err => setError(String(err)))
  }

  const handleAcceptSignal = (signalId: string) => {
    updateSignalReviewState(workspacePath, signalId, 'accepted_risk')
      .then(setSnapshotAndSelection)
      .catch(err => setError(String(err)))
  }

  const handleVerification = () => {
    if (!snapshot || !command.trim()) return
    runVerificationCommand(workspacePath, snapshot.snapshot_id, command.trim())
      .then(run => {
        setVerificationRun(run)
        return fetchCurrentSnapshot(workspacePath)
      })
      .then(setSnapshotAndSelection)
      .catch(err => setError(String(err)))
  }

  const handlePrecommitRebuild = () => {
    rebuildPrecommitReview(workspacePath)
      .then(data => {
        setSnapshot(data)
        setSnapshotNotReady(false)
        setSelectedFileId(data.files[0]?.file_id ?? null)
      })
      .catch(err => setError(String(err)))
  }

  const handleViewEvidence = (runId: string) => {
    fetchVerificationRun(workspacePath, runId)
      .then(setEvidenceRun)
      .catch(err => setError(String(err)))
  }

  const handleLanguageChange = (nextLanguage: Language) => {
    setLanguage(nextLanguage)
    storeLanguage(nextLanguage)
  }

  if (error) return <div className={styles.center}>{error}</div>
  if (snapshotNotReady) {
    return (
      <div className={styles.center}>
        <div className={styles.startCard}>
          <h1>Pre-commit Review</h1>
          <p>{language === 'zh-CN' ? '还没有提交前审查快照。请先启动本地质量闸门。' : 'No pre-commit review snapshot exists yet. Start the local quality gate first.'}</p>
          <button className={styles.button} onClick={handlePrecommitRebuild}>
            {language === 'zh-CN' ? '启动提交前审查' : 'Start pre-commit review'}
          </button>
        </div>
      </div>
    )
  }
  if (!snapshot) return <div className={styles.center}>{t(language, 'loading')}</div>

  return (
    <div className={styles.page}>
      {assessment
        ? (
          <AssessmentSummaryBar
            manifest={assessment}
            activeModule={activeModule}
            isRebuilding={isAssessmentRebuilding}
            rebuildJob={assessmentJob}
            onRebuild={rebuildAssessment}
            language={language}
            onLanguageChange={handleLanguageChange}
          />
        )
        : (
          <AgenticAssessmentFallback
            error={assessmentError ?? assessmentRebuildError}
            isRebuilding={isAssessmentRebuilding}
            job={assessmentJob}
            language={language}
            onLanguageChange={handleLanguageChange}
            onRebuild={rebuildAssessment}
          />
        )}
      <header className={styles.summaryBar}>
        <div>
          <div className={styles.title}>Pre-commit Review</div>
          <div className={styles.meta}>
            {snapshot.review_target} · {visibleFiles.length} {activeModule === 'tests' ? t(language, 'testFiles') : t(language, 'stagedFiles')} · {snapshot.summary.message}
          </div>
          <nav className={styles.nav} aria-label="precommit modules">
            <button
              aria-pressed={activeModule === 'review'}
              className={activeModule === 'review' ? styles.activeNav : undefined}
              onClick={() => setActiveModule('review')}
            >
              {t(language, 'review')}
            </button>
            <button
              aria-pressed={activeModule === 'tests'}
              className={activeModule === 'tests' ? styles.activeNav : undefined}
              onClick={() => setActiveModule('tests')}
            >
              {t(language, 'tests')}
            </button>
          </nav>
        </div>
        <div className={styles.summaryActions}>
          <div className={`${styles.decision} ${decisionClass(snapshot.decision)}`}>
            {translatedDecision(snapshot.decision, language)}
          </div>
        </div>
      </header>

      <main className={styles.workspace}>
        <FileList
          files={visibleFiles}
          selectedFileId={selectedFileId}
          onSelect={setSelectedFileId}
          title={activeModule === 'tests' ? t(language, 'testFiles') : t(language, 'stagedFiles')}
          language={language}
        />
        <HunkList file={selectedFile} hunks={selectedHunks} onReviewed={handleHunkReviewed} language={language} />
        <EvidencePanel
          snapshot={snapshot}
          selectedFile={selectedFile}
          selectedFileIds={new Set(visibleFiles.map(file => file.file_id))}
          command={command}
          verificationRun={verificationRun}
          evidenceRun={evidenceRun}
          language={language}
          onCommandChange={setCommand}
          onAcceptSignal={handleAcceptSignal}
          onRunVerification={handleVerification}
          onViewEvidence={handleViewEvidence}
        />
      </main>
    </div>
  )
}

function AgenticAssessmentFallback({
  error,
  isRebuilding,
  job,
  language,
  onLanguageChange,
  onRebuild,
}: {
  error: string | null
  isRebuilding: boolean
  job: JobState | null
  language: Language
  onLanguageChange: (language: Language) => void
  onRebuild: () => void
}) {
  return (
    <section className={styles.agentAssessmentShell} aria-label="assessment-summary">
      <div className={styles.agentAssessmentPrimary}>
        <h1>Agentic Change Assessment</h1>
        <p>{assessmentFallbackMessage(error, language)}</p>
        <div className={styles.agentAssessmentGrid}>
          <article>
            <h2>代码变更总览</h2>
            <p>{language === 'zh-CN' ? '等待重建后生成变更摘要。' : 'Waiting for rebuild to generate the change overview.'}</p>
          </article>
          <article>
            <h2>Codex 聊天和操作记录</h2>
            <p>{language === 'zh-CN' ? '等待采集本轮 agent 记录。' : 'Waiting to capture this round of agent records.'}</p>
          </article>
          <article>
            <h2>测试执行情况</h2>
            <p>{language === 'zh-CN' ? '等待汇总测试与验证证据。' : 'Waiting to summarize test and verification evidence.'}</p>
          </article>
          <article>
            <h2>Agent 总体评估</h2>
            <p>{language === 'zh-CN' ? '重建完成后给出提交建议。' : 'Commit guidance appears after rebuild completes.'}</p>
          </article>
        </div>
      </div>
      <div className={styles.agentAssessmentActions}>
        <div className={styles.languageToggle} aria-label={t(language, 'language')}>
          <button
            className={language === 'zh-CN' ? styles.activeLanguage : undefined}
            onClick={() => onLanguageChange('zh-CN')}
          >
            {t(language, 'simplifiedChinese')}
          </button>
          <button
            className={language === 'en-US' ? styles.activeLanguage : undefined}
            onClick={() => onLanguageChange('en-US')}
          >
            {t(language, 'english')}
          </button>
        </div>
        <RebuildButton isRebuilding={isRebuilding} onClick={onRebuild} language={language} />
        <RebuildProgress job={job} language={language} />
      </div>
    </section>
  )
}

function FileList({
  files,
  selectedFileId,
  onSelect,
  title,
  language,
}: {
  files: PrecommitFile[]
  selectedFileId: string | null
  onSelect: (fileId: string) => void
  title: string
  language: Language
}) {
  return (
    <aside className={styles.panel} aria-label="changed-files">
      <div className={styles.panelHeader}>
        <h2>{title}</h2>
        <span className={styles.count}>{files.length}</span>
      </div>
      <div className={styles.fileList}>
        {files.length === 0
          ? <div className={styles.empty}>{t(language, 'noPending')}</div>
          : files.map(file => (
            <button
              className={`${styles.fileButton} ${file.file_id === selectedFileId ? styles.selected : ''}`}
              key={file.file_id}
              onClick={() => onSelect(file.file_id)}
            >
              <strong>{file.path}</strong>
              <span className={styles.meta}>{file.review_state_summary} · {file.risk.band}</span>
              <span className={styles.diffStat}>{file.additions}+ {file.deletions}-</span>
            </button>
          ))}
      </div>
    </aside>
  )
}

function HunkList({
  file,
  hunks,
  onReviewed,
  language,
}: {
  file: PrecommitFile | null
  hunks: PrecommitHunk[]
  onReviewed: (hunk: PrecommitHunk) => void
  language: Language
}) {
  return (
    <main className={styles.panel} aria-label="file-diff">
      <div className={styles.panelHeader}>
        <div>
          <h2>{file?.path ?? t(language, 'noStagedFiles')}</h2>
          {file && <div className={styles.meta}>{file.additions} {t(language, 'additions')} · {file.deletions} {t(language, 'deletions')}</div>}
        </div>
      </div>
      <div className={styles.diffList}>
        {hunks.length === 0
          ? <div className={styles.empty}>{t(language, 'noHunks')}</div>
          : hunks.map(hunk => (
            <section className={styles.hunk} key={hunk.hunk_id}>
              <div className={styles.hunkHeader}>
                <span>{t(language, 'hunkStatus')}: {hunk.review_status}</span>
                <button className={styles.button} onClick={() => onReviewed(hunk)}>{t(language, 'markHunkReviewed')}</button>
              </div>
              {hunk.lines.map((line, index) => (
                <div className={`${styles.line} ${styles[line.type] ?? ''}`} key={`${hunk.hunk_id}-${index}`}>
                  <span>{linePrefix(line.type)}</span>
                  <span>{line.content}</span>
                </div>
              ))}
            </section>
          ))}
      </div>
    </main>
  )
}

function EvidencePanel({
  snapshot,
  selectedFile,
  selectedFileIds,
  command,
  verificationRun,
  evidenceRun,
  language,
  onCommandChange,
  onAcceptSignal,
  onRunVerification,
  onViewEvidence,
}: {
  snapshot: PrecommitSnapshot
  selectedFile: PrecommitFile | null
  selectedFileIds: Set<string>
  command: string
  verificationRun: VerificationRun | null
  evidenceRun: VerificationRun | null
  language: Language
  onCommandChange: (command: string) => void
  onAcceptSignal: (signalId: string) => void
  onRunVerification: () => void
  onViewEvidence: (runId: string) => void
}) {
  const visibleSignals = snapshot.signals.filter(signal => {
    if (signal.target_type === 'file') return selectedFileIds.has(signal.target_id)
    if (signal.target_type === 'hunk') {
      return snapshot.hunks.some(hunk => hunk.hunk_id === signal.target_id && selectedFileIds.has(hunk.file_id))
    }
    return true
  })
  const visibleQueue = snapshot.queue.filter(item => (
    selectedFileIds.has(item.target_id)
    || snapshot.hunks.some(hunk => hunk.hunk_id === item.target_id && selectedFileIds.has(hunk.file_id))
    || visibleSignals.some(signal => signal.signal_id === item.queue_id)
  ))

  return (
    <aside className={styles.panel} aria-label="file-evidence">
      <div className={styles.panelHeader}>
        <div>
          <h2>{t(language, 'evidence')}</h2>
          <div className={styles.meta}>{selectedFile?.path ?? t(language, 'noSelection')}</div>
        </div>
      </div>

      <div className={`${styles.decisionCard} ${decisionClass(snapshot.decision)}`}>
        {translatedDecision(snapshot.decision, language)}
      </div>
      {snapshot.stale && <div className={styles.banner}>{t(language, 'staleSnapshot')}</div>}
      {snapshot.workspace_changed_outside_target && (
        <div className={styles.banner}>{t(language, 'workspaceChangedOutsideTarget')}</div>
      )}

      <section className={styles.section}>
        <h3>{t(language, 'highRiskQueue')}</h3>
        <div className={styles.list} aria-label="unresolved review queue">
          {visibleQueue.length === 0
            ? <div className={styles.item}>{t(language, 'noUnresolved')}</div>
            : visibleQueue.map(item => (
              <div className={styles.item} key={item.queue_id}>
                <strong>P{item.priority}</strong>
                <div>{item.message}</div>
              </div>
            ))}
        </div>
      </section>

      {selectedFile && (
        <section className={styles.section}>
          <h3>{t(language, 'risk')}</h3>
          <div className={styles.item}>
            <div>{t(language, 'risk')} {selectedFile.risk.band} · score {selectedFile.risk.score}</div>
            <div>{selectedFile.additions} {t(language, 'additions')} · {selectedFile.deletions} {t(language, 'deletions')}</div>
          </div>
        </section>
      )}

      <section className={styles.section}>
        <h3>{t(language, 'signals')}</h3>
        <div className={styles.list}>
          {visibleSignals.map(signal => (
            <div className={styles.item} key={signal.signal_id}>
              <strong>{signal.severity}</strong>
              <div>{signal.message}</div>
              <div className={styles.meta}>{signal.status} · {signal.policy_rule_id}</div>
              {signal.evidence_ids.length > 0 && (
                <div className={styles.evidenceActions}>
                  {signal.evidence_ids.map(evidenceId => (
                    <button className={styles.button} key={evidenceId} onClick={() => onViewEvidence(evidenceId)}>
                      View evidence {evidenceId}
                    </button>
                  ))}
                </div>
              )}
              {signal.status === 'open' && (
                <button className={styles.button} onClick={() => onAcceptSignal(signal.signal_id)}>
                  {t(language, 'acceptRisk')}
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h3>{t(language, 'verification')}</h3>
        <div className={styles.inputRow}>
          <input
            aria-label="verification command"
            className={styles.input}
            value={command}
            onChange={event => onCommandChange(event.target.value)}
            placeholder="pytest"
          />
          <button className={styles.button} onClick={onRunVerification}>{t(language, 'runVerification')}</button>
        </div>
        {verificationRun && (
          <div className={styles.item}>
            {verificationRun.status} · exit {verificationRun.exit_code ?? 'unknown'} · {verificationRun.target_aligned ? t(language, 'aligned') : t(language, 'misaligned')}
          </div>
        )}
        {evidenceRun && (
          <div className={styles.item}>
            <strong>Evidence {evidenceRun.run_id}</strong>
            <div>{evidenceRun.status} · exit {evidenceRun.exit_code ?? 'unknown'} · {evidenceRun.target_aligned ? t(language, 'aligned') : t(language, 'misaligned')}</div>
            {evidenceRun.execution_mode && <div>{evidenceRun.execution_mode}</div>}
            {evidenceRun.raw_output_ref && <div>{evidenceRun.raw_output_ref}</div>}
          </div>
        )}
      </section>
    </aside>
  )
}
