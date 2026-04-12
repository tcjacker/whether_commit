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
}

function row(label: string, data: { status: string; passed?: number; total?: number }) {
  const detail =
    data.passed !== undefined && data.total !== undefined
      ? `${data.passed} / ${data.total}`
      : null
  return { label, status: data.status, detail }
}

export function VerificationCard({ status, loading, selectedModule, onSelectModule }: Props) {
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
      </div>
    </CardShell>
  )
}
