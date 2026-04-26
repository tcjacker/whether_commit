import type { ChangedFileSummary } from '../types/api'

function priority(file: ChangedFileSummary) {
  return file.highest_hunk_priority ?? -1
}

export function sortFilesByReviewPriority(files: ChangedFileSummary[]) {
  return [...files].sort((left, right) => {
    const priorityDelta = priority(right) - priority(left)
    if (priorityDelta !== 0) return priorityDelta
    const mismatchDelta = (right.mismatch_count ?? 0) - (left.mismatch_count ?? 0)
    if (mismatchDelta !== 0) return mismatchDelta
    return left.path.localeCompare(right.path)
  })
}
