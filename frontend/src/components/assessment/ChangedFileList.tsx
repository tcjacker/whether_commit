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
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
