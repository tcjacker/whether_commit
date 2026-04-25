import { useState, useEffect } from 'react'
import styles from './DiffViewer.module.css'

interface Props {
  repoKey: string
  filePath: string
  onClose: () => void
}

interface DiffLine {
  type: 'add' | 'remove' | 'context' | 'header'
  content: string
  lineNo?: number
}

function parseDiff(raw: string): DiffLine[] {
  const lines = raw.split('\n')
  const result: DiffLine[] = []
  for (const line of lines) {
    if (line.startsWith('+++') || line.startsWith('---')) continue
    if (line.startsWith('@@')) {
      result.push({ type: 'header', content: line })
    } else if (line.startsWith('+')) {
      result.push({ type: 'add', content: line.slice(1) })
    } else if (line.startsWith('-')) {
      result.push({ type: 'remove', content: line.slice(1) })
    } else {
      result.push({ type: 'context', content: line.startsWith(' ') ? line.slice(1) : line })
    }
  }
  return result
}

export function DiffViewer({ repoKey, filePath, onClose }: Props) {
  const [diff, setDiff] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    const params = new URLSearchParams({ repo_key: repoKey, file_path: filePath })
    fetch(`/api/changes/file-diff?${params}`)
      .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e.detail ?? '加载失败')))
      .then(data => { setDiff(data.diff); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }, [repoKey, filePath])

  const lines = diff ? parseDiff(diff) : []
  const shortName = filePath.split('/').pop() ?? filePath

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.panel} onClick={e => e.stopPropagation()}>
        <div className={styles.toolbar}>
          <span className={styles.fileName}>{filePath}</span>
          <button className={styles.closeBtn} onClick={onClose} aria-label="关闭差异视图">✕</button>
        </div>

        <div className={styles.body}>
          {loading && (
            <div className={styles.center}>正在加载 <code>{shortName}</code> 的差异…</div>
          )}
          {error && (
            <div className={styles.errorMsg}>{error}</div>
          )}
          {!loading && !error && lines.length === 0 && (
            <div className={styles.center}>该文件暂无可用差异。</div>
          )}
          {!loading && !error && lines.length > 0 && (
            <table className={styles.table}>
              <tbody>
                {lines.map((l, i) => (
                  <tr key={i} className={styles[l.type]}>
                    <td className={styles.gutter}>
                      {l.type === 'add' ? '+' : l.type === 'remove' ? '−' : l.type === 'header' ? '' : ' '}
                    </td>
                    <td className={styles.code}>{l.content}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
