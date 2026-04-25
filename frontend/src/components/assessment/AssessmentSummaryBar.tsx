import type { AssessmentManifest } from '../../types/api'
import styles from './AssessmentSummaryBar.module.css'

export function AssessmentSummaryBar({ manifest }: { manifest: AssessmentManifest }) {
  return (
    <section className={styles.bar} aria-label="assessment-summary">
      <div>
        <h1>Agentic Change Assessment</h1>
        <p>{manifest.summary.headline}</p>
      </div>
      <div className={styles.metrics}>
        <span>Risk: {manifest.summary.overall_risk_level}</span>
        <span>Coverage: {manifest.summary.coverage_status}</span>
        <span>Files: {manifest.summary.changed_file_count}</span>
        <span>Unreviewed: {manifest.review_progress.unreviewed}</span>
      </div>
    </section>
  )
}
