import { useEffect } from 'react'
import { fetchOverview, triggerRebuild } from '../api/overview'
import { useOverviewStore } from '../store/useOverviewStore'
import { ApiError } from '../api/client'

export function useOverview(repoKey: string) {
  const { setOverview, setLoadingState, setActiveJob } = useOverviewStore()

  useEffect(() => {
    if (!repoKey) return
    setLoadingState('loading')
    fetchOverview(repoKey)
      .then(data => setOverview(data))
      .catch(e => {
        if (e instanceof ApiError && e.status === 404) {
          setLoadingState('not_ready')
        } else {
          setLoadingState('error', e.message)
        }
      })
  }, [repoKey])

  const rebuild = async (workspacePath?: string) => {
    try {
      setLoadingState('rebuilding')
      const { job_id } = await triggerRebuild({ repo_key: repoKey, workspace_path: workspacePath })
      setActiveJob(job_id, null)
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setLoadingState('error', 'A rebuild is already running. Please wait.')
      } else {
        setLoadingState('error', e instanceof Error ? e.message : 'Failed to start rebuild.')
      }
    }
  }

  return { rebuild }
}
