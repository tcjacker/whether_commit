import type { ChangedFileSummary } from '../../types/api'
import styles from './ChangedFileList.module.css'

export function ChangedFileList({
  files,
  selectedFileId,
  onSelect,
}: {
  files: ChangedFileSummary[]
  selectedFileId: string | null
  onSelect: (file: ChangedFileSummary) => void
}) {
  return (
    <aside className={styles.panel} aria-label="changed-files">
      <h2>Changed Files</h2>
      {files.map(file => (
        <button
          key={file.file_id}
          className={file.file_id === selectedFileId ? styles.selected : styles.file}
          onClick={() => onSelect(file)}
        >
          <span>{file.path}</span>
          <small>{file.status} +{file.additions} -{file.deletions}</small>
        </button>
      ))}
    </aside>
  )
}
