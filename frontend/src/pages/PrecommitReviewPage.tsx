import { useEffect, useMemo, useState } from 'react'
import {
  fetchVerificationRun,
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
  const [evidenceRun, setEvidenceRun] = useState<VerificationRun | null>(null)
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

  const handleViewEvidence = (runId: string) => {
    fetchVerificationRun(workspacePath, runId)
      .then(setEvidenceRun)
      .catch(err => setError(String(err)))
  }

  if (error) return <div className={styles.center}>{error}</div>
  if (!snapshot) return <div className={styles.center}>Loading pre-commit review...</div>

  return (
    <div className={styles.page}>
      <header className={styles.summaryBar}>
        <div>
          <div className={styles.title}>Pre-commit Review</div>
          <div className={styles.meta}>
            {snapshot.review_target} · {snapshot.summary.changed_file_count} staged files · {snapshot.summary.message}
          </div>
        </div>
        <div className={styles.summaryActions}>
          <div className={`${styles.decision} ${decisionClass(snapshot.decision)}`}>
            {decisionLabel(snapshot.decision)}
          </div>
          <button className={styles.button} onClick={handleRebuild}>Rebuild</button>
        </div>
      </header>

      <main className={styles.workspace}>
        <FileList files={snapshot.files} selectedFileId={selectedFileId} onSelect={setSelectedFileId} />
        <HunkList file={selectedFile} hunks={selectedHunks} onReviewed={handleHunkReviewed} />
        <EvidencePanel
          snapshot={snapshot}
          selectedFile={selectedFile}
          command={command}
          verificationRun={verificationRun}
          evidenceRun={evidenceRun}
          onCommandChange={setCommand}
          onAcceptSignal={handleAcceptSignal}
          onRunVerification={handleVerification}
          onViewEvidence={handleViewEvidence}
        />
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
    <aside className={styles.panel} aria-label="changed-files">
      <div className={styles.panelHeader}>
        <h2>Staged Files</h2>
        <span className={styles.count}>{files.length}</span>
      </div>
      <div className={styles.fileList}>
        {files.length === 0
          ? <div className={styles.empty}>no pending staged changes</div>
          : files.map(file => (
            <button
              className={`${styles.fileButton} ${file.file_id === selectedFileId ? styles.selected : ''}`}
              key={file.file_id}
              onClick={() => onSelect(file.file_id)}
            >
              <strong>{file.path}</strong>
              <span className={styles.meta}>{file.review_state_summary} · {file.risk.band}</span>
              <span className={styles.diffStat}>{file.additions}+ {file.deletions}-</span>
            </button>
          ))}
      </div>
    </aside>
  )
}

function HunkList({
  file,
  hunks,
  onReviewed,
}: {
  file: PrecommitFile | null
  hunks: PrecommitHunk[]
  onReviewed: (hunk: PrecommitHunk) => void
}) {
  return (
    <main className={styles.panel} aria-label="file-diff">
      <div className={styles.panelHeader}>
        <div>
          <h2>{file?.path ?? 'No staged files'}</h2>
          {file && <div className={styles.meta}>{file.additions} additions · {file.deletions} deletions</div>}
        </div>
      </div>
      <div className={styles.diffList}>
        {hunks.length === 0
          ? <div className={styles.empty}>No hunks to review.</div>
          : hunks.map(hunk => (
            <section className={styles.hunk} key={hunk.hunk_id}>
              <div className={styles.hunkHeader}>
                <span>Hunk status: {hunk.review_status}</span>
                <button className={styles.button} onClick={() => onReviewed(hunk)}>Mark hunk reviewed</button>
              </div>
              {hunk.lines.map((line, index) => (
                <div className={`${styles.line} ${styles[line.type] ?? ''}`} key={`${hunk.hunk_id}-${index}`}>
                  <span>{linePrefix(line.type)}</span>
                  <span>{line.content}</span>
                </div>
              ))}
            </section>
          ))}
      </div>
    </main>
  )
}

function EvidencePanel({
  snapshot,
  selectedFile,
  command,
  verificationRun,
  evidenceRun,
  onCommandChange,
  onAcceptSignal,
  onRunVerification,
  onViewEvidence,
}: {
  snapshot: PrecommitSnapshot
  selectedFile: PrecommitFile | null
  command: string
  verificationRun: VerificationRun | null
  evidenceRun: VerificationRun | null
  onCommandChange: (command: string) => void
  onAcceptSignal: (signalId: string) => void
  onRunVerification: () => void
  onViewEvidence: (runId: string) => void
}) {
  return (
    <aside className={styles.panel} aria-label="file-evidence">
      <div className={styles.panelHeader}>
        <div>
          <h2>Evidence</h2>
          <div className={styles.meta}>{selectedFile?.path ?? 'No staged file selected'}</div>
        </div>
      </div>

      <div className={`${styles.decisionCard} ${decisionClass(snapshot.decision)}`}>
        {decisionLabel(snapshot.decision)}
      </div>
      {snapshot.stale && <div className={styles.banner}>stale snapshot</div>}
      {snapshot.workspace_changed_outside_target && (
        <div className={styles.banner}>workspace changed outside target</div>
      )}

      <section className={styles.section}>
        <h3>Unresolved Review Queue</h3>
        <div className={styles.list} aria-label="unresolved review queue">
          {snapshot.queue.length === 0
            ? <div className={styles.item}>No unresolved review items.</div>
            : snapshot.queue.map(item => (
              <div className={styles.item} key={item.queue_id}>
                <strong>P{item.priority}</strong>
                <div>{item.message}</div>
              </div>
            ))}
        </div>
      </section>

      {selectedFile && (
        <section className={styles.section}>
          <h3>Risk</h3>
          <div className={styles.item}>
            <div>Risk {selectedFile.risk.band} · score {selectedFile.risk.score}</div>
            <div>{selectedFile.additions} additions · {selectedFile.deletions} deletions</div>
          </div>
        </section>
      )}

      <section className={styles.section}>
        <h3>Signals</h3>
        <div className={styles.list}>
          {snapshot.signals.map(signal => (
            <div className={styles.item} key={signal.signal_id}>
              <strong>{signal.severity}</strong>
              <div>{signal.message}</div>
              <div className={styles.meta}>{signal.status} · {signal.policy_rule_id}</div>
              {signal.evidence_ids.length > 0 && (
                <div className={styles.evidenceActions}>
                  {signal.evidence_ids.map(evidenceId => (
                    <button className={styles.button} key={evidenceId} onClick={() => onViewEvidence(evidenceId)}>
                      View evidence {evidenceId}
                    </button>
                  ))}
                </div>
              )}
              {signal.status === 'open' && (
                <button className={styles.button} onClick={() => onAcceptSignal(signal.signal_id)}>
                  Accept risk
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h3>Verification</h3>
        <div className={styles.inputRow}>
          <input
            aria-label="verification command"
            className={styles.input}
            value={command}
            onChange={event => onCommandChange(event.target.value)}
            placeholder="pytest"
          />
          <button className={styles.button} onClick={onRunVerification}>Run verification</button>
        </div>
        {verificationRun && (
          <div className={styles.item}>
            {verificationRun.status} · exit {verificationRun.exit_code ?? 'unknown'} · {verificationRun.target_aligned ? 'aligned' : 'misaligned'}
          </div>
        )}
        {evidenceRun && (
          <div className={styles.item}>
            <strong>Evidence {evidenceRun.run_id}</strong>
            <div>{evidenceRun.status} · exit {evidenceRun.exit_code ?? 'unknown'} · {evidenceRun.target_aligned ? 'aligned' : 'misaligned'}</div>
            {evidenceRun.execution_mode && <div>{evidenceRun.execution_mode}</div>}
            {evidenceRun.raw_output_ref && <div>{evidenceRun.raw_output_ref}</div>}
          </div>
        )}
      </section>
    </aside>
  )
}
