import type { ChangedFileDetail } from '../../types/api'
import styles from './FileDiffReview.module.css'

export function FileDiffReview({ detail }: { detail: ChangedFileDetail | null }) {
  if (!detail) return <main className={styles.panel}>Select a file to review its diff.</main>
  return (
    <main className={styles.panel} aria-label="file-diff">
      <header>
        <h2>{detail.file.path}</h2>
        <span>+{detail.file.additions} -{detail.file.deletions}</span>
      </header>
      <div className={styles.diff}>
        {detail.diff_hunks.map(hunk => (
          <section key={hunk.hunk_id}>
            {hunk.lines.map((line, index) => (
              <pre key={`${hunk.hunk_id}-${index}`} className={styles[line.type]}>
                {line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' '}
                {line.content}
              </pre>
            ))}
          </section>
        ))}
      </div>
    </main>
  )
}
