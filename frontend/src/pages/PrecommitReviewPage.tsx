import { useEffect, useMemo, useState } from 'react'
import {
  fetchCurrentSnapshot,
  rebuildPrecommitReview,
  runVerificationCommand,
  updateHunkReviewState,
  updateSignalReviewState,
} from '../api/precommitReview'
import type { PrecommitFile, PrecommitHunk, PrecommitSnapshot, VerificationRun } from '../types/api'
import styles from './PrecommitReviewPage.module.css'

function getWorkspacePath() {
  return new URLSearchParams(window.location.search).get('workspace_path') ?? ''
}

function decisionClass(decision: string) {
  if (decision === 'no_known_blockers') return styles.good
  if (decision === 'not_recommended') return styles.bad
  return styles.review
}

function decisionLabel(decision: string) {
  return decision.replaceAll('_', ' ')
}

function linePrefix(type: string) {
  if (type === 'add') return '+'
  if (type === 'remove') return '-'
  return ' '
}

export function PrecommitReviewPage() {
  const workspacePath = getWorkspacePath()
  const [snapshot, setSnapshot] = useState<PrecommitSnapshot | null>(null)
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [command, setCommand] = useState('')
  const [verificationRun, setVerificationRun] = useState<VerificationRun | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCurrentSnapshot(workspacePath)
      .then(data => {
        setSnapshot(data)
        setSelectedFileId(data.files[0]?.file_id ?? null)
      })
      .catch(err => setError(String(err)))
  }, [workspacePath])

  const selectedFile = useMemo(
    () => snapshot?.files.find(file => file.file_id === selectedFileId) ?? null,
    [snapshot, selectedFileId],
  )
  const selectedHunks = useMemo(
    () => snapshot?.hunks.filter(hunk => hunk.file_id === selectedFileId) ?? [],
    [snapshot, selectedFileId],
  )

  const setSnapshotAndSelection = (next: PrecommitSnapshot) => {
    setSnapshot(next)
    setSelectedFileId(current => current ?? next.files[0]?.file_id ?? null)
  }

  const handleRebuild = () => {
    rebuildPrecommitReview(workspacePath)
      .then(setSnapshotAndSelection)
      .catch(err => setError(String(err)))
  }

  const handleHunkReviewed = (hunk: PrecommitHunk) => {
    updateHunkReviewState(workspacePath, hunk.hunk_id, 'reviewed')
      .then(setSnapshotAndSelection)
      .catch(err => setError(String(err)))
  }

  const handleAcceptSignal = (signalId: string) => {
    updateSignalReviewState(workspacePath, signalId, 'accepted_risk')
      .then(setSnapshotAndSelection)
      .catch(err => setError(String(err)))
  }

  const handleVerification = () => {
    if (!snapshot || !command.trim()) return
    runVerificationCommand(workspacePath, snapshot.snapshot_id, command.trim())
      .then(run => {
        setVerificationRun(run)
        return fetchCurrentSnapshot(workspacePath)
      })
      .then(setSnapshotAndSelection)
      .catch(err => setError(String(err)))
  }

  if (error) return <div className={styles.center}>{error}</div>
  if (!snapshot) return <div className={styles.center}>Loading pre-commit review...</div>

  return (
    <div className={styles.page}>
      <header className={styles.topbar}>
        <div>
          <div className={styles.title}>Pre-commit Review</div>
          <div className={styles.meta}>{snapshot.review_target} · {snapshot.summary.message}</div>
        </div>
        <button className={styles.button} onClick={handleRebuild}>Rebuild</button>
      </header>

      <main className={styles.workspace}>
        <section className={styles.panel}>
          <div className={`${styles.decision} ${decisionClass(snapshot.decision)}`}>
            {decisionLabel(snapshot.decision)}
          </div>
          {snapshot.stale && <div className={styles.banner}>stale snapshot</div>}
          {snapshot.workspace_changed_outside_target && (
            <div className={styles.banner}>workspace changed outside target</div>
          )}

          <div className={styles.list} aria-label="review queue">
            {snapshot.queue.length === 0
              ? <div className={styles.item}>No open review queue items.</div>
              : snapshot.queue.map(item => (
                <div className={styles.item} key={item.queue_id}>
                  <strong>P{item.priority}</strong>
                  <div>{item.message}</div>
                </div>
              ))}
          </div>
        </section>

        <section className={styles.panel}>
          <FileList files={snapshot.files} selectedFileId={selectedFileId} onSelect={setSelectedFileId} />
          <HunkList hunks={selectedHunks} onReviewed={handleHunkReviewed} />
        </section>

        <section className={styles.panel}>
          <h2>{selectedFile?.path ?? 'No staged files'}</h2>
          {selectedFile && (
            <div className={styles.item}>
              <div>Risk {selectedFile.risk.band} · score {selectedFile.risk.score}</div>
              <div>{selectedFile.additions} additions · {selectedFile.deletions} deletions</div>
            </div>
          )}

          <div className={styles.list}>
            {snapshot.signals.map(signal => (
              <div className={styles.item} key={signal.signal_id}>
                <strong>{signal.severity}</strong>
                <div>{signal.message}</div>
                <div className={styles.meta}>{signal.status} · {signal.policy_rule_id}</div>
                {signal.status === 'open' && (
                  <button className={styles.button} onClick={() => handleAcceptSignal(signal.signal_id)}>
                    Accept risk
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className={styles.inputRow}>
            <input
              aria-label="verification command"
              className={styles.input}
              value={command}
              onChange={event => setCommand(event.target.value)}
              placeholder="pytest"
            />
            <button className={styles.button} onClick={handleVerification}>Run verification</button>
          </div>
          {verificationRun && (
            <div className={styles.item}>
              {verificationRun.status} · exit {verificationRun.exit_code ?? 'unknown'} · {verificationRun.target_aligned ? 'aligned' : 'misaligned'}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

function FileList({
  files,
  selectedFileId,
  onSelect,
}: {
  files: PrecommitFile[]
  selectedFileId: string | null
  onSelect: (fileId: string) => void
}) {
  return (
    <div className={styles.list} aria-label="staged files">
      {files.length === 0
        ? <div className={styles.item}>no pending staged changes</div>
        : files.map(file => (
          <button
            className={`${styles.fileButton} ${file.file_id === selectedFileId ? styles.selected : ''}`}
            key={file.file_id}
            onClick={() => onSelect(file.file_id)}
          >
            <strong>{file.path}</strong>
            <div className={styles.meta}>{file.risk.band} · {file.additions}+ {file.deletions}-</div>
          </button>
        ))}
    </div>
  )
}

function HunkList({ hunks, onReviewed }: { hunks: PrecommitHunk[], onReviewed: (hunk: PrecommitHunk) => void }) {
  return (
    <div className={styles.list}>
      {hunks.map(hunk => (
        <div className={styles.hunk} key={hunk.hunk_id}>
          {hunk.lines.map((line, index) => (
            <div className={`${styles.line} ${styles[line.type] ?? ''}`} key={`${hunk.hunk_id}-${index}`}>
              <span>{linePrefix(line.type)}</span>
              <span>{line.content}</span>
            </div>
          ))}
          <button className={styles.button} onClick={() => onReviewed(hunk)}>Mark hunk reviewed</button>
        </div>
      ))}
    </div>
  )
}
