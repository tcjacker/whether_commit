import type { ChangeRiskSummary } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { StatusBadge } from '../shared/StatusBadge'
import styles from './ChangeRiskSummaryCard.module.css'

interface Props {
  summary: ChangeRiskSummary | null
  loading: boolean
}

const RISK_LABELS: Record<string, string> = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
  unknown: '未知',
}

export function ChangeRiskSummaryCard({ summary, loading }: Props) {
  if (loading || !summary) {
    return (
      <CardShell title="变更风险总览">
        <div className={styles.loading}>
          <SkeletonBlock height={20} width="60%" />
          <SkeletonBlock height={14} lines={3} />
          <SkeletonBlock height={14} width="45%" />
        </div>
      </CardShell>
    )
  }

  return (
    <CardShell
      title="变更风险总览"
      subtitle={summary.coverage.coverage_summary}
      badge={<StatusBadge status="warning" label={RISK_LABELS[summary.headline.overall_risk_level] ?? '未知'} />}
    >
      <div className={styles.content}>
        <section className={styles.section}>
          <p className={styles.summary}>{summary.headline.overall_risk_summary}</p>
          {summary.headline.recommended_focus.length > 0 && (
            <ul className={styles.focusList}>
              {summary.headline.recommended_focus.map(item => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </section>

        <section className={styles.section}>
          <div className={styles.metrics}>
            <span>关联测试 {summary.coverage.affected_test_count}</span>
            <span>已验证路径 {summary.coverage.verified_changed_path_count}</span>
            <span>未验证路径 {summary.coverage.unverified_changed_path_count}</span>
          </div>
          {summary.coverage.missing_test_paths.length > 0 && (
            <p className={styles.caption}>缺失测试：{summary.coverage.missing_test_paths.join('、')}</p>
          )}
        </section>

        <section className={styles.section}>
          <p className={styles.caption}>{summary.existing_feature_impact.business_impact_summary}</p>
          <ul className={styles.capabilityList}>
            {summary.existing_feature_impact.affected_capabilities.map(item => (
              <li key={item.capability_key} className={styles.capabilityItem}>
                <div className={styles.capabilityHeader}>
                  <strong>{item.name}</strong>
                  <StatusBadge status={item.verification_status} />
                </div>
                {item.technical_entrypoints.length > 0 && (
                  <p className={styles.caption}>技术入口：{item.technical_entrypoints.join('、')}</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </CardShell>
  )
}
