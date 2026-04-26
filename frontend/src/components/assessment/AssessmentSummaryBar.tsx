import type { AssessmentManifest } from '../../types/api'
import { RebuildButton } from '../rebuild/RebuildButton'
import { RebuildProgress } from '../rebuild/RebuildProgress'
import styles from './AssessmentSummaryBar.module.css'
import type { JobState } from '../../types/api'

function formatValue(value: string) {
  return value.replaceAll('_', ' ')
}

function decisionAdvice(decision: string) {
  if (decision === 'safe_to_commit') return '可以提交：当前没有明显阻断信号，但仍建议完成未审文件的人工确认。'
  if (decision === 'needs_tests') return '暂不建议提交：需要补强测试证据后再提交。'
  if (decision === 'needs_recheck') return '暂不建议直接提交：需要先复查高优先级 hunk 和影响面。'
  if (decision === 'do_not_commit_yet') return '不建议提交：存在高严重度冲突或失败证据，需要先修复。'
  return '暂不建议提交：当前证据不足，需要先完成审查。'
}

function agentRecommendation(manifest: AssessmentManifest) {
  const decision = manifest.review_decision ?? 'unknown'
  const topHunk = manifest.hunk_queue_preview?.[0]
  const suggestions: string[] = []

  if (topHunk) {
    const reason = topHunk.reasons[0] ? `：${topHunk.reasons[0]}` : ''
    suggestions.push(`优先看 ${topHunk.path} ${topHunk.hunk_id} (P${topHunk.priority})${reason}`)
  }
  if ((manifest.mismatch_count ?? 0) > 0) {
    suggestions.push(`处理 ${manifest.mismatch_count} 个 claim/fact mismatch`)
  }
  if ((manifest.weak_test_evidence_count ?? 0) > 0 || manifest.summary.coverage_status !== 'covered') {
    suggestions.push('确认测试证据是否达到 direct/indirect')
  }
  if (manifest.review_progress.unreviewed > 0) {
    suggestions.push(`完成 ${manifest.review_progress.unreviewed} 个未审文件`)
  }

  return [decisionAdvice(decision), suggestions.slice(0, 3).join('；')].filter(Boolean).join(' ')
}

export function AssessmentSummaryBar({
  manifest,
  activeModule = 'review',
  isRebuilding = false,
  rebuildJob = null,
  onRebuild,
}: {
  manifest: AssessmentManifest
  activeModule?: 'review' | 'tests'
  isRebuilding?: boolean
  rebuildJob?: JobState | null
  onRebuild?: () => void
}) {
  const query = window.location.search
  const agenticSummary = manifest.agentic_summary
  const mode = manifest.mode ?? 'working_tree'
  const provenanceCapture = manifest.provenance_capture_level ?? agenticSummary.capture_level
  const reviewDecision = manifest.review_decision ?? 'unknown'
  const changedFilesText = `${manifest.summary.changed_file_count} files, risk ${manifest.summary.overall_risk_level}, coverage ${manifest.summary.coverage_status}`
  const codexText = `capture ${agenticSummary.capture_level}, provenance ${formatValue(provenanceCapture)}, confidence ${agenticSummary.confidence}`
  const testText = `${manifest.summary.missing_test_count} missing, ${manifest.weak_test_evidence_count ?? 0} weak evidence, coverage ${manifest.summary.coverage_status}`
  const verdictText = `${formatValue(reviewDecision)} · ${manifest.mismatch_count ?? 0} mismatch · ${manifest.review_progress.unreviewed} unreviewed`
  const recommendationText = agentRecommendation(manifest)

  return (
    <section className={styles.bar} aria-label="assessment-summary">
      <div className={styles.primary}>
        <h1>Agentic Change Assessment</h1>
        <p>{manifest.summary.headline}</p>
        {agenticSummary.main_objective && (
          <div className={styles.roundSummary}>
            <header>
              <strong>本轮目标</strong>
              <span>{formatValue(mode)}</span>
            </header>
            <p className={styles.objective}>{agenticSummary.main_objective}</p>
            <div className={styles.briefGrid}>
              <article>
                <h2>代码变更总览</h2>
                <p>{changedFilesText}</p>
                <small>{manifest.summary.recommended_review_order.slice(0, 3).join(', ') || 'No changed files.'}</small>
              </article>
              <article>
                <h2>Codex 聊天和操作记录</h2>
                <p>{codexText}</p>
                <small>{agenticSummary.user_design_goal || '未捕获到结构化 Codex 设计目标'}</small>
              </article>
              <article>
                <h2>测试执行情况</h2>
                <p>{testText}</p>
                <small>{agenticSummary.tests_and_verification[0] || '未捕获到已执行测试命令。'}</small>
              </article>
              <article className={styles.verdict}>
                <h2>Agent 总体评估</h2>
                <p>{verdictText}</p>
                <small>{recommendationText}</small>
              </article>
            </div>
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
        {onRebuild && (
          <div className={styles.rebuild}>
            <RebuildButton isRebuilding={isRebuilding} onClick={onRebuild} />
            <RebuildProgress job={rebuildJob} />
          </div>
        )}
      </div>
    </section>
  )
}
