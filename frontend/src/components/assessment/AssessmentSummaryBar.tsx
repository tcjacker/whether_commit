import type { AssessmentManifest, JobState } from '../../types/api'
import { formatMismatchCount, formatValue, t, type Language } from '../../i18n'
import { RebuildButton } from '../rebuild/RebuildButton'
import { RebuildProgress } from '../rebuild/RebuildProgress'
import styles from './AssessmentSummaryBar.module.css'

function decisionAdvice(decision: string, language: Language) {
  if (language === 'en-US') {
    if (decision === 'safe_to_commit') return 'Can commit: no obvious blocking signal is present, but manual confirmation of unreviewed files is still recommended.'
    if (decision === 'needs_tests') return 'Do not commit yet: strengthen test evidence before committing.'
    if (decision === 'needs_recheck') return 'Do not commit directly: recheck high-priority hunks and impact first.'
    if (decision === 'do_not_commit_yet') return 'Do not commit: high-severity conflicts or failed evidence need fixes first.'
    return 'Do not commit yet: current evidence is insufficient and review should be completed first.'
  }
  if (decision === 'safe_to_commit') return '可以提交：当前没有明显阻断信号，但仍建议完成未审文件的人工确认。'
  if (decision === 'needs_tests') return '暂不建议提交：需要补强测试证据后再提交。'
  if (decision === 'needs_recheck') return '暂不建议直接提交：需要先复查高优先级 hunk 和影响面。'
  if (decision === 'do_not_commit_yet') return '不建议提交：存在高严重度冲突或失败证据，需要先修复。'
  return '暂不建议提交：当前证据不足，需要先完成审查。'
}

function agentRecommendation(manifest: AssessmentManifest, language: Language) {
  const decision = manifest.review_decision ?? 'unknown'
  const topHunk = manifest.hunk_queue_preview?.[0]
  const suggestions: string[] = []

  if (topHunk) {
    const reason = topHunk.reasons[0] ? `${language === 'zh-CN' ? '：' : ': '}${topHunk.reasons[0]}` : ''
    suggestions.push(language === 'zh-CN'
      ? `优先看 ${topHunk.path} ${topHunk.hunk_id} (P${topHunk.priority})${reason}`
      : `Review ${topHunk.path} ${topHunk.hunk_id} (P${topHunk.priority}) first${reason}`)
  }
  if ((manifest.mismatch_count ?? 0) > 0) {
    suggestions.push(language === 'zh-CN'
      ? `处理 ${manifest.mismatch_count} 个 claim/fact mismatch`
      : `Resolve ${formatMismatchCount(manifest.mismatch_count ?? 0, language)}`)
  }
  if ((manifest.weak_test_evidence_count ?? 0) > 0 || manifest.summary.coverage_status !== 'covered') {
    suggestions.push(language === 'zh-CN' ? '确认测试证据是否达到 direct/indirect' : 'Confirm whether test evidence reaches direct/indirect')
  }
  if (manifest.review_progress.unreviewed > 0) {
    suggestions.push(language === 'zh-CN'
      ? `完成 ${manifest.review_progress.unreviewed} 个未审文件`
      : `Review ${manifest.review_progress.unreviewed} unreviewed ${manifest.review_progress.unreviewed === 1 ? 'file' : 'files'}`)
  }

  return [decisionAdvice(decision, language), suggestions.slice(0, 3).join(language === 'zh-CN' ? '；' : '; ')].filter(Boolean).join(' ')
}

export function AssessmentSummaryBar({
  manifest,
  activeModule = 'review',
  isRebuilding = false,
  rebuildJob = null,
  onRebuild,
  language,
  onLanguageChange,
}: {
  manifest: AssessmentManifest
  activeModule?: 'review' | 'tests'
  isRebuilding?: boolean
  rebuildJob?: JobState | null
  onRebuild?: () => void
  language: Language
  onLanguageChange: (language: Language) => void
}) {
  const query = window.location.search
  const agenticSummary = manifest.agentic_summary
  const mode = manifest.mode ?? 'working_tree'
  const provenanceCapture = manifest.provenance_capture_level ?? agenticSummary.capture_level
  const reviewDecision = manifest.review_decision ?? 'unknown'
  const changedFilesText = language === 'zh-CN'
    ? `${manifest.summary.changed_file_count} 个文件，风险 ${manifest.summary.overall_risk_level}，覆盖 ${manifest.summary.coverage_status}`
    : `${manifest.summary.changed_file_count} files, risk ${manifest.summary.overall_risk_level}, coverage ${manifest.summary.coverage_status}`
  const codexText = language === 'zh-CN'
    ? `捕获 ${agenticSummary.capture_level}，溯源 ${formatValue(provenanceCapture, language)}，置信度 ${agenticSummary.confidence}`
    : `capture ${agenticSummary.capture_level}, provenance ${formatValue(provenanceCapture, language)}, confidence ${agenticSummary.confidence}`
  const testText = language === 'zh-CN'
    ? `${manifest.summary.missing_test_count} 个缺失，${manifest.weak_test_evidence_count ?? 0} 个弱证据，覆盖 ${manifest.summary.coverage_status}`
    : `${manifest.summary.missing_test_count} missing, ${manifest.weak_test_evidence_count ?? 0} weak evidence, coverage ${manifest.summary.coverage_status}`
  const verdictText = language === 'zh-CN'
    ? `${formatValue(reviewDecision, language)} · ${manifest.mismatch_count ?? 0} 个不一致 · ${manifest.review_progress.unreviewed} 个未审`
    : `${formatValue(reviewDecision, language)} · ${manifest.mismatch_count ?? 0} mismatch · ${manifest.review_progress.unreviewed} unreviewed`
  const recommendationText = agentRecommendation(manifest, language)

  return (
    <section className={styles.bar} aria-label="assessment-summary">
      <div className={styles.primary}>
        <h1>Agentic Change Assessment</h1>
        <p>{manifest.summary.headline}</p>
        {agenticSummary.main_objective && (
          <div className={styles.roundSummary}>
            <header>
              <strong>{t(language, 'thisRoundGoal')}</strong>
              <span>{formatValue(mode, language)}</span>
            </header>
            <p className={styles.objective}>{agenticSummary.main_objective}</p>
            <div className={styles.briefGrid}>
              <article>
                <h2>{t(language, 'codeChangeOverview')}</h2>
                <p>{changedFilesText}</p>
                <small>{manifest.summary.recommended_review_order.slice(0, 3).join(', ') || t(language, 'noChangedFiles')}</small>
              </article>
              <article>
                <h2>{t(language, 'codexRecords')}</h2>
                <p>{codexText}</p>
                <small>{agenticSummary.user_design_goal || t(language, 'noStructuredGoal')}</small>
              </article>
              <article>
                <h2>{t(language, 'testExecution')}</h2>
                <p>{testText}</p>
                <small>{agenticSummary.tests_and_verification[0] || t(language, 'noTestCommands')}</small>
              </article>
              <article className={styles.verdict}>
                <h2>{t(language, 'agentOverallAssessment')}</h2>
                <p>{verdictText}</p>
                <small>{recommendationText}</small>
              </article>
            </div>
          </div>
        )}
        <nav className={styles.nav} aria-label="assessment-modules">
          <a className={activeModule === 'review' ? styles.active : undefined} href={`/${query}`}>
            {t(language, 'review')}
          </a>
          <a className={activeModule === 'tests' ? styles.active : undefined} href={`/tests${query}`}>
            {t(language, 'tests')}
          </a>
        </nav>
      </div>
      <div className={styles.metrics}>
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
        {onRebuild && (
          <div className={styles.rebuild}>
            <RebuildButton isRebuilding={isRebuilding} onClick={onRebuild} language={language} />
            <RebuildProgress job={rebuildJob} language={language} />
          </div>
        )}
      </div>
    </section>
  )
}
