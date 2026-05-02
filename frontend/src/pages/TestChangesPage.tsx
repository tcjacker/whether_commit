import { useCallback, useEffect, useRef, useState } from 'react'
import {
  analyzeAssessmentTestResult,
  fetchAssessmentTestCaseDetail,
  fetchAssessmentTests,
  fetchLatestAssessment,
  runAssessmentTestCommand,
} from '../api/assessments'
import { TestCaseList } from '../components/tests/TestCaseList'
import { TestEvidencePanel } from '../components/tests/TestEvidencePanel'
import { TestResultPanel } from '../components/tests/TestResultPanel'
import { useAssessmentRebuild } from '../hooks/useAssessmentRebuild'
import { readStoredLanguage, storeLanguage, t, type Language } from '../i18n'
import type {
  AssessmentManifest,
  TestCaseDetail,
  TestCaseSummary,
  TestManagementSummary,
  TestResultAnalysis,
} from '../types/api'
import styles from './TestChangesPage.module.css'

function getParams() {
  const p = new URLSearchParams(window.location.search)
  return {
    repoKey: p.get('repo_key') ?? 'divide_prd_to_ui',
    workspacePath: p.get('workspace_path') ?? '',
  }
}

function firstTestCase(summary: TestManagementSummary): TestCaseSummary | null {
  return summary.files[0]?.test_cases[0] ?? null
}

export function TestChangesPage() {
  const { repoKey, workspacePath } = getParams()
  const detailRequestId = useRef(0)
  const [manifest, setManifest] = useState<AssessmentManifest | null>(null)
  const [testSummary, setTestSummary] = useState<TestManagementSummary | null>(null)
  const [selectedTestCaseId, setSelectedTestCaseId] = useState<string | null>(null)
  const [detail, setDetail] = useState<TestCaseDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [language, setLanguage] = useState<Language>(() => readStoredLanguage())

  const loadAssessment = useCallback(async () => {
    const latest = await fetchLatestAssessment(repoKey, workspacePath)

    try {
      const tests = await fetchAssessmentTests(repoKey, latest.assessment_id, workspacePath)
      setError(null)
      setManifest(latest)
      setTestSummary(tests)
      const initialTestCase = firstTestCase(tests)
      setSelectedTestCaseId(initialTestCase?.test_case_id ?? null)
      setDetail(null)
    } catch (err) {
      setManifest(latest)
      setTestSummary(null)
      setSelectedTestCaseId(null)
      setDetail(null)
      setError(`Test management data is not ready: ${String(err)}`)
    }

    return latest
  }, [repoKey, workspacePath])

  const { rebuild, isRebuilding, job, rebuildError } = useAssessmentRebuild(repoKey, workspacePath, loadAssessment)

  useEffect(() => {
    let cancelled = false
    const timer = window.setTimeout(() => {
      if (cancelled) return
      loadAssessment()
        .catch(err => {
          if (!cancelled) setError(String(err))
        })
    }, 0)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [loadAssessment])

  useEffect(() => {
    const requestId = ++detailRequestId.current
    if (!manifest || !selectedTestCaseId) {
      return
    }
    const assessmentId = manifest.assessment_id
    const testCaseId = selectedTestCaseId
    let cancelled = false
    const isCurrentRequest = () => !cancelled && requestId === detailRequestId.current

    fetchAssessmentTestCaseDetail(repoKey, assessmentId, testCaseId, workspacePath)
      .then(data => {
        if (isCurrentRequest()) setDetail(data)
      })
      .catch(err => {
        if (isCurrentRequest()) setError(`Test case detail is not ready: ${String(err)}`)
      })

    return () => {
      cancelled = true
    }
  }, [repoKey, workspacePath, manifest, selectedTestCaseId])

  const handleSelect = (testCase: TestCaseSummary) => {
    setSelectedTestCaseId(testCase.test_case_id)
    setDetail(null)
  }

  const handleLanguageChange = (nextLanguage: Language) => {
    setLanguage(nextLanguage)
    storeLanguage(nextLanguage)
  }

  const handleRunCommand = async (command: TestCaseDetail['recommended_commands'][number]) => {
    if (!manifest || !selectedTestCaseId) throw new Error('No selected test case.')
    const result = await runAssessmentTestCommand(
      repoKey,
      manifest.assessment_id,
      selectedTestCaseId,
      command.command_id,
      workspacePath,
    )
    const refreshed = await fetchAssessmentTestCaseDetail(repoKey, manifest.assessment_id, selectedTestCaseId, workspacePath)
    setDetail(refreshed)
    return result
  }

  const handleAnalyzeResult = async (runId: string): Promise<TestResultAnalysis> => {
    if (!manifest || !selectedTestCaseId) throw new Error('No selected test case.')
    const analysis = await analyzeAssessmentTestResult(
      repoKey,
      manifest.assessment_id,
      selectedTestCaseId,
      runId,
      workspacePath,
    )
    const refreshed = await fetchAssessmentTestCaseDetail(repoKey, manifest.assessment_id, selectedTestCaseId, workspacePath)
    setDetail(refreshed)
    return analysis
  }

  const displayError = error ?? rebuildError

  if (displayError) return <div className={styles.center}>{displayError}</div>
  if (!manifest || !testSummary) return <div className={styles.center}>{t(language, 'loadingAssessment')}</div>

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>{t(language, 'testManagement')}</p>
          <h1>{t(language, 'testPageTitle')}</h1>
          <p className={styles.subtitle}>
            {language === 'zh-CN'
              ? `${testSummary.test_case_count} 个测试用例，覆盖 ${testSummary.changed_test_file_count} 个变更测试文件。`
              : `${testSummary.test_case_count} test cases across ${testSummary.changed_test_file_count} changed test files.`}
          </p>
        </div>
        <div className={styles.actions}>
          <div className={styles.languageToggle} aria-label={t(language, 'language')}>
            <button
              type="button"
              className={language === 'zh-CN' ? styles.activeLanguage : undefined}
              onClick={() => handleLanguageChange('zh-CN')}
            >
              {t(language, 'simplifiedChinese')}
            </button>
            <button
              type="button"
              className={language === 'en-US' ? styles.activeLanguage : undefined}
              onClick={() => handleLanguageChange('en-US')}
            >
              {t(language, 'english')}
            </button>
          </div>
          <div className={styles.actionRow}>
            <a href={`/${window.location.search}`}>{t(language, 'review')}</a>
            <button type="button" disabled={isRebuilding} onClick={rebuild}>
              {isRebuilding ? t(language, 'rebuilding') : t(language, 'rebuild')}
            </button>
          </div>
        </div>
      </header>
      {job ? (
        <p className={styles.rebuildStatus}>
          {job.step}: {job.message} ({job.progress}%)
        </p>
      ) : null}
      {testSummary.test_case_count === 0 ? (
        <section className={styles.emptyState}>
          <h2>{t(language, 'testPageEmptyTitle')}</h2>
          <p>{t(language, 'testPageEmptyBody')}</p>
        </section>
      ) : null}
      <div className={styles.workspace}>
        <TestCaseList
          summary={testSummary}
          selectedTestCaseId={selectedTestCaseId}
          onSelect={handleSelect}
          language={language}
        />
        <TestResultPanel detail={detail} onRunCommand={handleRunCommand} onAnalyzeResult={handleAnalyzeResult} language={language} />
        <TestEvidencePanel detail={detail} language={language} />
      </div>
    </div>
  )
}
