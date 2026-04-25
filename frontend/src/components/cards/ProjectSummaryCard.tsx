import type { ProjectSummary } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { zhChangeType, zhConfidence } from '../../i18n'
import styles from './ProjectSummaryCard.module.css'

interface Props {
  summary: ProjectSummary | null
  loading: boolean
}

type ImpactBasisEntry = string | Record<string, unknown>

type ProjectSummaryDisplay = ProjectSummary & {
  overall_assessment?: string
  impact_level?: 'high' | 'medium' | 'low' | 'unknown' | string
  impact_basis?: ImpactBasisEntry[]
  affected_capability_count?: number
  affected_entrypoints?: string[]
  critical_paths?: string[]
  verification_gaps?: string[]
  priority_themes?: string[]
  degraded_hint?: string
}

const IMPACT_LEVEL_LABELS: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
  unknown: '未知',
}

function zhImpactLevel(level: string | undefined): string {
  if (!level) return '未知'
  return IMPACT_LEVEL_LABELS[level] ?? level
}

function isDegraded(summary: ProjectSummaryDisplay): boolean {
  if (summary.degraded_hint) return true
  return /fallback|unavailable|降级/i.test(summary.overall_assessment ?? '')
}

function formatBasisEntry(entry: ImpactBasisEntry): { title: string; detail?: string } {
  if (typeof entry === 'string') {
    return { title: entry }
  }

  const subject =
    stringValue(entry.target_id) ??
    stringValue(entry.entity_id) ??
    stringValue(entry.path) ??
    stringValue(entry.route) ??
    stringValue(entry.symbol) ??
    stringValue(entry.module_id)

  const reason =
    stringValue(entry.reason) ??
    stringValue(entry.summary) ??
    stringValue(entry.message) ??
    stringValue(entry.label)

  const evidence = entry.evidence
  const evidenceDetail = Array.isArray(evidence)
    ? `${evidence.length} 条证据`
    : evidence
      ? stringValue(evidence) ?? '已有证据'
      : undefined

  const title = [subject, reason].filter(Boolean).join(' · ') || JSON.stringify(entry)
  return {
    title,
    detail: evidenceDetail,
  }
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined
}

export function ProjectSummaryCard({ summary, loading }: Props) {
  const displaySummary = summary as ProjectSummaryDisplay | null
  const degraded = displaySummary ? isDegraded(displaySummary) : false
  const impactBasis = displaySummary?.impact_basis ?? []

  return (
    <CardShell title="项目摘要">
      {loading || !summary ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <SkeletonBlock height={20} width="80%" />
          <SkeletonBlock height={14} lines={3} />
          <SkeletonBlock height={14} width="60%" />
        </div>
      ) : (
        <div className={styles.content}>
          <p className={styles.main}>{displaySummary?.overall_assessment || summary.what_this_app_seems_to_do || '—'}</p>

          <div className={styles.summaryMeta}>
            <div className={styles.field}>
              <span className={styles.label}>影响等级</span>
              <span>{zhImpactLevel(displaySummary?.impact_level)}</span>
            </div>

            {displaySummary?.affected_capability_count !== undefined && (
              <div className={styles.field}>
                <span className={styles.label}>受影响能力</span>
                <span>{displaySummary.affected_capability_count} 项</span>
              </div>
            )}

            {displaySummary?.affected_entrypoints?.length ? (
              <div className={styles.field}>
                <span className={styles.label}>受影响入口</span>
                <span>{displaySummary.affected_entrypoints.join('、')}</span>
              </div>
            ) : null}

            {displaySummary?.critical_paths?.length ? (
              <div className={styles.field}>
                <span className={styles.label}>关键路径</span>
                <span>{displaySummary.critical_paths.join('、')}</span>
              </div>
            ) : null}

            {displaySummary?.verification_gaps?.length ? (
              <div className={styles.field}>
                <span className={styles.label}>验证缺口</span>
                <span>{displaySummary.verification_gaps.join('、')}</span>
              </div>
            ) : null}
          </div>

          {displaySummary?.priority_themes?.length ? (
            <div className={styles.section}>
              <span className={styles.label}>优先主题</span>
              <div className={styles.tags}>
                {displaySummary.priority_themes.map(theme => (
                  <span key={theme} className={styles.tag}>{theme}</span>
                ))}
              </div>
            </div>
          ) : null}

          {impactBasis.length > 0 && (
            <div className={styles.section}>
              <span className={styles.label}>影响依据</span>
              <ul className={styles.basisList}>
                {impactBasis.map((entry, index) => {
                  const basis = formatBasisEntry(entry)
                  return (
                    <li key={index} className={styles.basisItem}>
                      <span className={styles.basisTitle}>{basis.title}</span>
                      {basis.detail && <span className={styles.basisDetail}>{basis.detail}</span>}
                    </li>
                  )
                })}
              </ul>
            </div>
          )}

          {degraded && (
            <div className={styles.hintBox}>
              <span className={styles.hintLabel}>降级提示</span>
              <span className={styles.hintText}>
                {displaySummary?.degraded_hint || '当前结论来自源代码静态分析，Agent 判定未能稳定接入。'}
              </span>
            </div>
          )}

          {summary.core_flow && (
            <div className={styles.field}>
              <span className={styles.label}>核心流程</span>
              <span>{summary.core_flow}</span>
            </div>
          )}

          {summary.agent_reasoning?.technical_change_summary && (
            <div className={styles.field}>
              <span className={styles.label}>最近 AI 关注点</span>
              <span>{summary.agent_reasoning.technical_change_summary}</span>
            </div>
          )}

          {summary.agent_reasoning?.change_types?.length ? (
            <div className={styles.tags}>
              {summary.agent_reasoning.change_types.map(t => (
                <span key={t} className={styles.tag}>{zhChangeType(t)}</span>
              ))}
            </div>
          ) : null}

          {summary.technical_narrative && (
            <p className={styles.narrative}>{summary.technical_narrative}</p>
          )}

          {summary.agent_reasoning?.confidence && (
            <div className={styles.confidence}>
              置信度：<strong>{zhConfidence(summary.agent_reasoning.confidence)}</strong>
            </div>
          )}
        </div>
      )}
    </CardShell>
  )
}
