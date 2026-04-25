import { useEffect } from 'react'
import { fetchOverview, triggerRebuild } from '../api/overview'
import { useOverviewStore } from '../store/useOverviewStore'
import { ApiError } from '../api/client'

export function useOverview(repoKey: string, workspacePath?: string) {
  const { setOverview, setLoadingState, setActiveJob } = useOverviewStore()

  useEffect(() => {
    if (!repoKey) return
    setLoadingState('loading')
    fetchOverview(repoKey, undefined, workspacePath)
      .then(data => setOverview(data))
      .catch(e => {
        if (e instanceof ApiError && e.status === 404) {
          setLoadingState('not_ready')
        } else {
          setLoadingState('error', e.message)
        }
      })
  }, [repoKey, workspacePath])

  const rebuild = async (workspacePath?: string) => {
    const normalizedWorkspacePath = workspacePath?.trim()
    if (!normalizedWorkspacePath) {
      setLoadingState('error', '请先填写 workspace_path。')
      return
    }

    try {
      setLoadingState('rebuilding')
      const { job_id } = await triggerRebuild({ repo_key: repoKey, workspace_path: normalizedWorkspacePath })
      setActiveJob(job_id, null)
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setLoadingState('error', '已有重建任务正在运行，请稍候。')
      } else {
        setLoadingState('error', e instanceof Error ? e.message : '启动重建失败。')
      }
    }
  }

  return { rebuild }
}
