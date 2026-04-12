import { useEffect, useRef } from 'react'
import { fetchJob } from '../api/jobs'
import { fetchOverview } from '../api/overview'
import { useOverviewStore } from '../store/useOverviewStore'
import { ApiError } from '../api/client'

const POLL_INTERVAL_MS = 2000

export function useJobPoller(repoKey: string) {
  const { activeJobId, setActiveJob, setOverview, setLoadingState } = useOverviewStore()
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!activeJobId) {
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }

    timerRef.current = setInterval(async () => {
      try {
        const job = await fetchJob(activeJobId)
        setActiveJob(activeJobId, job)

        if (job.status === 'success' || job.status === 'partial_success') {
          clearInterval(timerRef.current!)
          setActiveJob(null, null)
          try {
            const overview = await fetchOverview(repoKey)
            setOverview(overview)
          } catch {
            setLoadingState('error', 'Rebuild succeeded but could not load overview.')
          }
        } else if (job.status === 'failed') {
          clearInterval(timerRef.current!)
          setActiveJob(null, null)
          setLoadingState('error', job.message || 'Rebuild failed.')
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) {
          clearInterval(timerRef.current!)
          setActiveJob(null, null)
        }
      }
    }, POLL_INTERVAL_MS)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [activeJobId, repoKey])
}
