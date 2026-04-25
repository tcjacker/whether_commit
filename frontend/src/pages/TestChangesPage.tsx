import { useEffect, useState } from 'react'
import { fetchAssessmentFileDetail, fetchLatestAssessment } from '../api/assessments'
import { AssessmentSummaryBar } from '../components/assessment/AssessmentSummaryBar'
import { ChangedFileList } from '../components/assessment/ChangedFileList'
import { FileDiffReview } from '../components/assessment/FileDiffReview'
import { FileEvidencePanel } from '../components/assessment/FileEvidencePanel'
import type { AssessmentManifest, ChangedFileDetail, ChangedFileSummary } from '../types/api'
import { isTestFile } from '../utils/testFiles'
import styles from './AssessmentReviewPage.module.css'

function getParams() {
  const p = new URLSearchParams(window.location.search)
  return {
    repoKey: p.get('repo_key') ?? 'divide_prd_to_ui',
    workspacePath: p.get('workspace_path') ?? '',
  }
}

export function TestChangesPage() {
  const { repoKey, workspacePath } = getParams()
  const [manifest, setManifest] = useState<AssessmentManifest | null>(null)
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [detail, setDetail] = useState<ChangedFileDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchLatestAssessment(repoKey, workspacePath)
      .then(data => {
        setManifest(data)
        setSelectedFileId(data.file_list.find(file => isTestFile(file.path))?.file_id ?? null)
      })
      .catch(err => setError(String(err)))
  }, [repoKey, workspacePath])

  useEffect(() => {
    if (!manifest || !selectedFileId) return
    fetchAssessmentFileDetail(repoKey, manifest.assessment_id, selectedFileId, workspacePath)
      .then(setDetail)
      .catch(err => setError(String(err)))
  }, [repoKey, workspacePath, manifest, selectedFileId])

  const handleSelect = (file: ChangedFileSummary) => {
    setSelectedFileId(file.file_id)
  }

  if (error) return <div className={styles.center}>{error}</div>
  if (!manifest) return <div className={styles.center}>Loading test changes...</div>

  const testFiles = manifest.file_list.filter(file => isTestFile(file.path))

  return (
    <div className={styles.page}>
      <AssessmentSummaryBar manifest={manifest} activeModule="tests" />
      <div className={styles.workspace}>
        <ChangedFileList files={testFiles} selectedFileId={selectedFileId} onSelect={handleSelect} title="Test Files" />
        <FileDiffReview detail={detail} />
        <FileEvidencePanel detail={detail} />
      </div>
    </div>
  )
}
