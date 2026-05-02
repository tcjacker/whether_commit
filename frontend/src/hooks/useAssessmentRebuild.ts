import { useEffect, useState } from 'react'
import { triggerAssessmentRebuild } from '../api/assessments'
import { fetchJob } from '../api/jobs'
import type { AssessmentManifest, JobState } from '../types/api'

type ReloadAssessment = () => Promise<AssessmentManifest>

export function useAssessmentRebuild(repoKey: string, workspacePath: string, reloadAssessment: ReloadAssessment) {
  const [job, setJob] = useState<JobState | null>(null)
  const [isRebuilding, setIsRebuilding] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!job || !['pending', 'running'].includes(job.status)) return
    const timer = window.setInterval(() => {
      fetchJob(job.job_id)
        .then(async nextJob => {
          setJob(nextJob)
          if (nextJob.status === 'success' || nextJob.status === 'partial_success') {
            try {
              await reloadAssessment()
              setJob(null)
            } finally {
              setIsRebuilding(false)
            }
          }
          if (nextJob.status === 'failed') {
            setError(nextJob.message || 'Assessment rebuild failed.')
            setIsRebuilding(false)
          }
        })
        .catch(err => {
          setError(String(err))
          setIsRebuilding(false)
        })
    }, 1000)
    return () => window.clearInterval(timer)
  }, [job, reloadAssessment])

  const rebuild = async () => {
    if (isRebuilding) return
    setError(null)
    setIsRebuilding(true)
    try {
      const response = await triggerAssessmentRebuild({
        repo_key: repoKey,
        workspace_path: workspacePath || undefined,
        base_commit_sha: 'AUTO_MERGE_BASE',
      })
      setJob({
        job_id: response.job_id,
        repo_key: repoKey,
        status: 'pending',
        step: 'init',
        progress: 0,
        message: 'Assessment rebuild queued.',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
    } catch (err) {
      setError(String(err))
      setIsRebuilding(false)
    }
  }

  return { rebuild, isRebuilding, job, rebuildError: error }
}
