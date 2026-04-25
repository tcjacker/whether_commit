import { useCallback, useEffect, useState } from 'react'
import { fetchAssessmentFileDetail, fetchLatestAssessment, triggerFileAgentAssessment } from '../api/assessments'
import { AssessmentSummaryBar } from '../components/assessment/AssessmentSummaryBar'
import { ChangedFileList } from '../components/assessment/ChangedFileList'
import { FileDiffReview } from '../components/assessment/FileDiffReview'
import { FileEvidencePanel } from '../components/assessment/FileEvidencePanel'
import { useAssessmentRebuild } from '../hooks/useAssessmentRebuild'
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

function minimumVisibleDelay(ms = 900) {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

export function TestChangesPage() {
  const { repoKey, workspacePath } = getParams()
  const [manifest, setManifest] = useState<AssessmentManifest | null>(null)
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [detail, setDetail] = useState<ChangedFileDetail | null>(null)
  const [agentRunningFileId, setAgentRunningFileId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadAssessment = useCallback(() => fetchLatestAssessment(repoKey, workspacePath)
    .then(data => {
      setManifest(data)
      setSelectedFileId(data.file_list.find(file => isTestFile(file.path))?.file_id ?? null)
      return data
    }), [repoKey, workspacePath])

  const { rebuild, isRebuilding, job, rebuildError } = useAssessmentRebuild(repoKey, workspacePath, loadAssessment)

  useEffect(() => {
    loadAssessment()
      .catch(err => setError(String(err)))
  }, [loadAssessment])

  useEffect(() => {
    if (rebuildError) setError(rebuildError)
  }, [rebuildError])

  useEffect(() => {
    if (!manifest || !selectedFileId) return
    fetchAssessmentFileDetail(repoKey, manifest.assessment_id, selectedFileId, workspacePath)
      .then(setDetail)
      .catch(err => setError(String(err)))
  }, [repoKey, workspacePath, manifest, selectedFileId])

  const handleSelect = (file: ChangedFileSummary) => {
    setSelectedFileId(file.file_id)
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
            unknowns: ['Codex agent assessment is running.'],
          },
        }
      : current)
    Promise.all([
      triggerFileAgentAssessment(repoKey, manifest.assessment_id, selectedFileId, workspacePath),
      minimumVisibleDelay(),
    ])
      .then(([updatedDetail]) => setDetail(updatedDetail))
      .catch(err => setError(String(err)))
      .finally(() => setAgentRunningFileId(null))
  }

  if (error) return <div className={styles.center}>{error}</div>
  if (!manifest) return <div className={styles.center}>Loading test changes...</div>

  const testFiles = manifest.file_list.filter(file => isTestFile(file.path))

  return (
    <div className={styles.page}>
      <AssessmentSummaryBar
        manifest={manifest}
        activeModule="tests"
        isRebuilding={isRebuilding}
        rebuildJob={job}
        onRebuild={rebuild}
      />
      <div className={styles.workspace}>
        <ChangedFileList files={testFiles} selectedFileId={selectedFileId} onSelect={handleSelect} title="Test Files" />
        <FileDiffReview detail={detail} />
        <FileEvidencePanel detail={detail} onRunAgent={handleRunAgent} running={agentRunningFileId === selectedFileId} />
      </div>
    </div>
  )
}
