import { useState } from 'react'
import type { VerificationStatus } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { StatusBadge } from '../shared/StatusBadge'
import styles from './VerificationCard.module.css'

interface Props {
  status: VerificationStatus | null
  loading: boolean
  selectedModule: string | null
  onSelectModule: (mod: string | null) => void
  repoKey: string
  workspacePath?: string
}

function row(label: string, data: { status: string; passed?: number; total?: number }) {
  const detail =
    data.passed !== undefined && data.total !== undefined
      ? `${data.passed} / ${data.total}`
      : null
  return { label, status: data.status, detail }
}

interface RunResult {
  status: string
  passed: number
  total: number
  duration_ms: number
  detail: string
}

export function VerificationCard({ status, loading, selectedModule, onSelectModule, repoKey, workspacePath }: Props) {
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState<RunResult | null>(null)
  const [runError, setRunError] = useState<string | null>(null)

  const handleRunTests = async () => {
    if (!workspacePath) return
    setRunning(true)
    setRunResult(null)
    setRunError(null)
    try {
      const resp = await fetch('/api/verification/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_key: repoKey, workspace_path: workspacePath }),
      })
      const data = await resp.json()
      if (!resp.ok) {
        setRunError(data.detail ?? 'Unknown error')
      } else {
        setRunResult(data)
      }
    } catch (e) {
      setRunError(String(e))
    } finally {
      setRunning(false)
    }
  }

  if (loading || !status) {
    return (
      <CardShell title="Verification Status">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[1, 2, 3, 4].map(i => <SkeletonBlock key={i} height={32} />)}
        </div>
      </CardShell>
    )
  }

  const rows = [
    row('Build', status.build),
    row('Unit tests', status.unit_tests),
    row('Integration tests', status.integration_tests),
    row('Scenario replay', status.scenario_replay),
  ]

  const unverifiedModules = [
    ...new Set([
      ...status.unverified_changed_modules,
      ...status.unverified_changed_paths,
    ]),
  ]

  return (
    <CardShell title="Verification Status">
      <div className={styles.content}>
        <div className={styles.rows}>
          {rows.map(r => (
            <div key={r.label} className={styles.row}>
              <span className={styles.rowLabel}>{r.label}</span>
              <div className={styles.rowRight}>
                {r.detail && <span className={styles.detail}>{r.detail}</span>}
                <StatusBadge status={r.status} />
              </div>
            </div>
          ))}
        </div>

        {unverifiedModules.length > 0 && (
          <div className={styles.section}>
            <p className={styles.sectionTitle}>Unverified changed areas</p>
            <ul className={styles.moduleList}>
              {unverifiedModules.map(m => {
                const isSelected = selectedModule === m
                return (
                  <li
                    key={m}
                    className={`${styles.module} ${isSelected ? styles.selected : ''}`}
                    onClick={() => onSelectModule(isSelected ? null : m)}
                  >
                    <span className={styles.warningDot} />
                    <span className={styles.moduleName}>{m}</span>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {status.unverified_areas.length > 0 && (
          <div className={styles.section}>
            <p className={styles.sectionTitle}>Unverified areas</p>
            <ul className={styles.areaList}>
              {status.unverified_areas.map((a, i) => (
                <li key={i} className={styles.area}>⚠ {a}</li>
              ))}
            </ul>
          </div>
        )}

        {workspacePath && (
          <div className={styles.runSection}>
            <button
              className={styles.runBtn}
              onClick={handleRunTests}
              disabled={running}
            >
              {running ? 'Running…' : 'Run Tests'}
            </button>

            {runResult && (
              <div className={`${styles.runResult} ${runResult.status === 'passed' ? styles.runPassed : styles.runFailed}`}>
                <span className={styles.runStatus}>
                  {runResult.status === 'passed' ? '✓' : '✗'} {runResult.passed}/{runResult.total} passed
                </span>
                <span className={styles.runDuration}>
                  {(runResult.duration_ms / 1000).toFixed(1)}s
                </span>
                {runResult.detail && (
                  <span className={styles.runDetail}>{runResult.detail}</span>
                )}
              </div>
            )}

            {runError && (
              <div className={styles.runError}>{runError}</div>
            )}
          </div>
        )}
      </div>
    </CardShell>
  )
}
