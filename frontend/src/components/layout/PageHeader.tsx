import type { RepoInfo, SnapshotInfo, JobState } from '../../types/api'
import type { LoadingState } from '../../store/useOverviewStore'
import { RebuildButton } from '../rebuild/RebuildButton'
import { RebuildProgress } from '../rebuild/RebuildProgress'
import styles from './PageHeader.module.css'

interface Props {
  repo: RepoInfo | null
  repoKey: string
  workspacePath: string
  snapshot: SnapshotInfo | null
  loadingState: LoadingState
  jobProgress: JobState | null
  onRebuild: () => void
  onWorkspacePathChange: (value: string) => void
  onClearSelection: () => void
  hasSelection: boolean
}

export function PageHeader({
  repo,
  repoKey,
  workspacePath,
  snapshot,
  loadingState,
  jobProgress,
  onRebuild,
  onWorkspacePathChange,
  onClearSelection,
  hasSelection,
}: Props) {
  const isRebuilding = loadingState === 'rebuilding'
  const reviewGraphParams = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath.trim()) {
    reviewGraphParams.set('workspace_path', workspacePath.trim())
  }

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <div className={styles.logo}>
          <svg width="20" height="20" viewBox="0 0 16 16" fill="var(--accent-light)">
            <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0zm1.5 4.5a.5.5 0 0 0-1 0v3.79L5.35 9.65a.5.5 0 1 0 .7.7l3-2.5A.5.5 0 0 0 9.5 7.5V4.5z"/>
          </svg>
          <span className={styles.appName}>应用总览</span>
        </div>
        {repo && (
          <div className={styles.repoInfo}>
            <span className={styles.repoName}>{repo.name}</span>
            <span className={styles.branch}>⎇ {repo.default_branch}</span>
            {snapshot?.has_pending_changes && (
              <span className={styles.pendingBadge}>● 存在待分析变更</span>
            )}
          </div>
        )}
      </div>

      <div className={styles.right}>
        <label className={styles.pathField}>
          <span className={styles.pathLabel}>Workspace Path</span>
          <input
            aria-label="Workspace Path"
            className={styles.pathInput}
            type="text"
            value={workspacePath}
            onChange={(event) => onWorkspacePathChange(event.target.value)}
            placeholder="/path/to/repo"
            spellCheck={false}
          />
        </label>
        <a className={styles.reviewLink} href={`/review-graph?${reviewGraphParams.toString()}`}>
          进入 Change Review
        </a>
        {hasSelection && (
          <button className={styles.clearBtn} onClick={onClearSelection}>
            ✕ 清除选择
          </button>
        )}
        {isRebuilding && jobProgress && (
          <RebuildProgress job={jobProgress} />
        )}
        <RebuildButton isRebuilding={isRebuilding} onClick={onRebuild} />
      </div>
    </header>
  )
}
