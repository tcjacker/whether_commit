export function buildReviewGraphUrl(repoKey?: string, changeId?: string): string {
  const params = new URLSearchParams()
  if (repoKey) params.set('repo_key', repoKey)
  if (changeId) params.set('change_id', changeId)
  const query = params.toString()
  return query ? `/review-graph?${query}` : '/review-graph'
}
