import type { ChangedFileDetail } from '../../types/api'
import { t, type Language } from '../../i18n'
import styles from './FileDiffReview.module.css'

export function FileDiffReview({ detail, language = 'en-US' }: { detail: ChangedFileDetail | null, language?: Language }) {
  if (!detail) return <main className={styles.panel}>{t(language, 'selectFileForDiff')}</main>
  const hunkItems = detail.hunk_review_items ?? []
  return (
    <main className={styles.panel} aria-label="file-diff">
      <header>
        <h2>{detail.file.path}</h2>
        <span>+{detail.file.additions} -{detail.file.deletions}</span>
      </header>
      <div className={styles.diff}>
        {detail.diff_hunks.map(hunk => (
          <section key={hunk.hunk_id} id={hunk.hunk_id} className={styles.hunk}>
            <div className={styles.hunkHeader}>
              <span>{hunk.hunk_id}</span>
              {hunkItems
                .filter(item => item.hunk_id === hunk.hunk_id)
                .map(item => (
                  <strong key={item.hunk_id}>{t(language, 'priority')} {item.priority}</strong>
                ))}
            </div>
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
