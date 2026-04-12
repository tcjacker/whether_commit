import { get } from './client'
import type { JobState } from '../types/api'

export function fetchJob(jobId: string): Promise<JobState> {
  return get<JobState>(`/api/jobs/${jobId}`)
}
