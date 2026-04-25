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
  const agenticSummary = manifest.agentic_summary

  return (
    <section className={styles.bar} aria-label="assessment-summary">
      <div className={styles.primary}>
        <h1>Agentic Change Assessment</h1>
        <p>{manifest.summary.headline}</p>
        {agenticSummary.main_objective && (
          <div className={styles.roundSummary}>
            <strong>本轮目标</strong>
            <p>{agenticSummary.main_objective}</p>
            <small>
              用户目标：{agenticSummary.user_design_goal || '未捕获到结构化 Codex 设计目标'}
            </small>
            <small>
              Codex 变更：{agenticSummary.codex_change_summary || '未捕获到结构化 Codex 变更摘要'}
            </small>
          </div>
        )}
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
        <span>Agent summary: {agenticSummary.capture_level}</span>
        <span>Confidence: {agenticSummary.confidence}</span>
        <span>Risk: {manifest.summary.overall_risk_level}</span>
        <span>Coverage: {manifest.summary.coverage_status}</span>
        <span>Files: {manifest.summary.changed_file_count}</span>
        <span>Unreviewed: {manifest.review_progress.unreviewed}</span>
      </div>
    </section>
  )
}
