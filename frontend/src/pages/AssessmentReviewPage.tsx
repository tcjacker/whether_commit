import { useCallback, useEffect, useState } from 'react'
import { fetchAssessmentFileDetail, fetchLatestAssessment, triggerFileAgentAssessment } from '../api/assessments'
import { AssessmentSummaryBar } from '../components/assessment/AssessmentSummaryBar'
import { ChangedFileList } from '../components/assessment/ChangedFileList'
import { FileDiffReview } from '../components/assessment/FileDiffReview'
import { FileEvidencePanel } from '../components/assessment/FileEvidencePanel'
import { useAssessmentRebuild } from '../hooks/useAssessmentRebuild'
import { readStoredLanguage, storeLanguage, t, type Language } from '../i18n'
import type { AssessmentManifest, ChangedFileDetail, ChangedFileSummary } from '../types/api'
import { withV02PreviewDetail, withV02PreviewManifest } from '../utils/assessmentPreview'
import { sortFilesByReviewPriority } from '../utils/assessmentSorting'
import { isTestFile } from '../utils/testFiles'
import styles from './AssessmentReviewPage.module.css'

function getParams() {
  const p = new URLSearchParams(window.location.search)
  return {
    repoKey: p.get('repo_key') ?? 'divide_prd_to_ui',
    workspacePath: p.get('workspace_path') ?? '',
    previewV02: p.get('aca_preview') === 'v02',
  }
}

function minimumVisibleDelay(ms = 900) {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

export function AssessmentReviewPage() {
  const { repoKey, workspacePath, previewV02 } = getParams()
  const [manifest, setManifest] = useState<AssessmentManifest | null>(null)
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [detail, setDetail] = useState<ChangedFileDetail | null>(null)
  const [agentRunningFileId, setAgentRunningFileId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [language, setLanguage] = useState<Language>(() => readStoredLanguage())

  const loadAssessment = useCallback(() => fetchLatestAssessment(repoKey, workspacePath)
    .then(data => {
      const assessment = previewV02 ? withV02PreviewManifest(data) : data
      const reviewFiles = sortFilesByReviewPriority(assessment.file_list.filter(file => !isTestFile(file.path)))
      setManifest(assessment)
      setSelectedFileId(reviewFiles[0]?.file_id ?? null)
      return assessment
    }), [repoKey, workspacePath, previewV02])

  const { rebuild, isRebuilding, job, rebuildError } = useAssessmentRebuild(repoKey, workspacePath, loadAssessment)

  useEffect(() => {
    loadAssessment()
      .catch(err => setError(String(err)))
  }, [loadAssessment])

  useEffect(() => {
    if (!manifest || !selectedFileId) return
    fetchAssessmentFileDetail(repoKey, manifest.assessment_id, selectedFileId, workspacePath)
      .then(data => setDetail(previewV02 ? withV02PreviewDetail(data) : data))
      .catch(err => setError(String(err)))
  }, [repoKey, workspacePath, manifest, selectedFileId, previewV02])

  const handleSelect = (file: ChangedFileSummary) => {
    setSelectedFileId(file.file_id)
  }

  const handleLanguageChange = (nextLanguage: Language) => {
    setLanguage(nextLanguage)
    storeLanguage(nextLanguage)
  }

  const handleRunAgent = () => {
    if (!manifest || !selectedFileId || agentRunningFileId) return
    setAgentRunningFileId(selectedFileId)
    setDetail(current => current
      ? {
          ...current,
          file_assessment: {
            ...current.file_assessment,
            agent_status: 'running',
            agent_source: 'codex',
            unknowns: [language === 'zh-CN' ? 'Codex agent 分析运行中。' : 'Codex agent assessment is running.'],
          },
        }
      : current)
    Promise.all([
      triggerFileAgentAssessment(repoKey, manifest.assessment_id, selectedFileId, workspacePath, language),
      minimumVisibleDelay(),
    ])
      .then(([updatedDetail]) => setDetail(updatedDetail))
      .catch(err => setError(String(err)))
      .finally(() => setAgentRunningFileId(null))
  }

  const displayError = error ?? rebuildError

  if (displayError) return <div className={styles.center}>{displayError}</div>
  if (!manifest) return <div className={styles.center}>{t(language, 'loadingAssessment')}</div>

  const reviewFiles = sortFilesByReviewPriority(manifest.file_list.filter(file => !isTestFile(file.path)))

  return (
    <div className={styles.page}>
      <AssessmentSummaryBar
        manifest={manifest}
        activeModule="review"
        isRebuilding={isRebuilding}
        rebuildJob={job}
        onRebuild={rebuild}
        language={language}
        onLanguageChange={handleLanguageChange}
      />
      <div className={styles.workspace}>
        <ChangedFileList files={reviewFiles} selectedFileId={selectedFileId} onSelect={handleSelect} />
        <FileDiffReview detail={detail} />
        <FileEvidencePanel detail={detail} onRunAgent={handleRunAgent} running={agentRunningFileId === selectedFileId} />
      </div>
    </div>
  )
}
