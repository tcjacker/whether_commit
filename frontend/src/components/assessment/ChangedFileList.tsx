import type { ChangedFileSummary } from '../../types/api'
import styles from './ChangedFileList.module.css'

export function ChangedFileList({
  files,
  selectedFileId,
  onSelect,
  title = 'Changed Files',
}: {
  files: ChangedFileSummary[]
  selectedFileId: string | null
  onSelect: (file: ChangedFileSummary) => void
  title?: string
}) {
  return (
    <aside className={styles.panel} aria-label="changed-files">
      <header className={styles.header}>
        <h2>{title}</h2>
        <span>{files.length}</span>
      </header>
      <ul className={styles.list}>
        {files.map(file => (
          <li key={file.file_id}>
            <button
              className={file.file_id === selectedFileId ? styles.selected : styles.file}
              onClick={() => onSelect(file)}
            >
              <span className={styles.path}>{file.path}</span>
              <span className={styles.meta}>{file.status} +{file.additions} -{file.deletions}</span>
              {(file.highest_hunk_priority || file.mismatch_count || file.weakest_test_evidence_grade) && (
                <span className={styles.badges}>
                  {file.highest_hunk_priority ? <span>Priority {file.highest_hunk_priority}</span> : null}
                  {file.mismatch_count ? <span>{file.mismatch_count} mismatch</span> : null}
                  {file.weakest_test_evidence_grade ? <span>{file.weakest_test_evidence_grade}</span> : null}
                </span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
