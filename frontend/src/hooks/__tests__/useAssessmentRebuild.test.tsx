import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAssessmentRebuild } from '../useAssessmentRebuild'
import { triggerAssessmentRebuild } from '../../api/assessments'
import { fetchJob } from '../../api/jobs'

vi.mock('../../api/assessments', () => ({
  triggerAssessmentRebuild: vi.fn(),
}))

vi.mock('../../api/jobs', () => ({
  fetchJob: vi.fn(),
}))

describe('useAssessmentRebuild', () => {
  beforeEach(() => {
    vi.mocked(triggerAssessmentRebuild).mockResolvedValue({ job_id: 'job_1', status: 'pending' })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('clears done progress after successful refresh so the idle button is not shown with closing text', async () => {
    vi.mocked(fetchJob).mockResolvedValue({
      job_id: 'job_1',
      repo_key: 'demo',
      status: 'success',
      step: 'done',
      progress: 100,
      message: 'done',
      created_at: '2026-04-26T00:00:00Z',
      updated_at: '2026-04-26T00:00:01Z',
    })

    const { result } = renderHook(() =>
      useAssessmentRebuild('demo', '/repo', () => Promise.resolve({} as never)),
    )

    await act(async () => {
      await result.current.rebuild()
    })

    await waitFor(() => expect(fetchJob).toHaveBeenCalledWith('job_1'), { timeout: 1500 })
    await waitFor(() => expect(result.current.isRebuilding).toBe(false))
    expect(result.current.job).toBeNull()
    expect(triggerAssessmentRebuild).toHaveBeenCalledWith({
      repo_key: 'demo',
      workspace_path: '/repo',
      base_commit_sha: 'AUTO_MERGE_BASE',
    })
  })
})
