import type { AssessmentManifest } from '../../types/api'
import styles from './AssessmentSummaryBar.module.css'

export function AssessmentSummaryBar({
  manifest,
  activeModule = 'review',
}: {
  manifest: AssessmentManifest
  activeModule?: 'review' | 'tests'
}) {
  const query = window.location.search

  return (
    <section className={styles.bar} aria-label="assessment-summary">
      <div>
        <h1>Agentic Change Assessment</h1>
        <p>{manifest.summary.headline}</p>
        <nav className={styles.nav} aria-label="assessment-modules">
          <a className={activeModule === 'review' ? styles.active : undefined} href={`/${query}`}>
            Review
          </a>
          <a className={activeModule === 'tests' ? styles.active : undefined} href={`/tests${query}`}>
            Tests
          </a>
        </nav>
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
