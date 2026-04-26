import { describe, expect, it } from 'vitest'
import { sortFilesByReviewPriority } from '../assessmentSorting'
import type { ChangedFileSummary } from '../../types/api'

function file(path: string, priority?: number, mismatchCount = 0): ChangedFileSummary {
  return {
    file_id: path,
    path,
    old_path: null,
    status: 'modified',
    additions: 1,
    deletions: 0,
    risk_level: 'low',
    coverage_status: 'unknown',
    review_status: 'unreviewed',
    agent_sources: ['git_diff'],
    diff_fingerprint: `sha256:${path}`,
    highest_hunk_priority: priority,
    mismatch_count: mismatchCount,
  }
}

describe('sortFilesByReviewPriority', () => {
  it('orders files by highest hunk priority before fallback path order', () => {
    const sorted = sortFilesByReviewPriority([
      file('frontend/vite.config.ts', 53),
      file('frontend/src/api/client.ts', 45),
      file('frontend/src/types/api.ts', 92),
      file('frontend/src/utils/assessmentPreview.ts'),
    ])

    expect(sorted.map(item => item.path)).toEqual([
      'frontend/src/types/api.ts',
      'frontend/vite.config.ts',
      'frontend/src/api/client.ts',
      'frontend/src/utils/assessmentPreview.ts',
    ])
  })

  it('uses mismatch count as a tie breaker', () => {
    const sorted = sortFilesByReviewPriority([
      file('b.ts', 60, 0),
      file('a.ts', 60, 2),
    ])

    expect(sorted.map(item => item.path)).toEqual(['a.ts', 'b.ts'])
  })
})
