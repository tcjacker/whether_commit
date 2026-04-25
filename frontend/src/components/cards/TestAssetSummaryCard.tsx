import type { TestAssetSummary } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { StatusBadge } from '../shared/StatusBadge'
import styles from './TestAssetSummaryCard.module.css'

interface Props {
  summary: TestAssetSummary | null
  loading: boolean
}

const HEALTH_LABELS: Record<TestAssetSummary['health_status'], string> = {
  healthy: '健康',
  needs_maintenance: '需维护',
  high_risk: '高风险',
  unknown: '未知',
}

const STATUS_LABELS: Record<string, string> = {
  covered: '已覆盖',
  partial: '部分覆盖',
  missing: '缺覆盖',
  unknown: '未知',
  keep: '保留',
  update: '更新',
  retire: '淘汰',
}

function badgeStatus(status: string) {
  if (status === 'healthy' || status === 'covered' || status === 'keep') return 'stable'
  if (status === 'high_risk' || status === 'missing' || status === 'retire') return 'warning'
  return 'running'
}

export function TestAssetSummaryCard({ summary, loading }: Props) {
  if (loading || !summary) {
    return (
      <CardShell title="测试资产健康">
        <div className={styles.loading}>
          <SkeletonBlock height={20} width="52%" />
          <SkeletonBlock height={14} lines={3} />
        </div>
      </CardShell>
    )
  }

  return (
    <CardShell
      title="测试资产健康"
      subtitle={`${summary.affected_test_count} 个相关测试 · ${summary.coverage_gaps.length} 条覆盖缺口`}
      badge={<StatusBadge status={badgeStatus(summary.health_status)} label={HEALTH_LABELS[summary.health_status]} />}
    >
      <div className={styles.content}>
        <div className={styles.metrics}>
          <span>测试文件 {summary.total_test_file_count}</span>
          <span>本次改动测试 {summary.changed_test_file_count}</span>
          <span>需整理 {summary.stale_or_invalid_test_count}</span>
          <span>重复低价值 {summary.duplicate_or_low_value_test_count}</span>
        </div>

        {summary.recommended_actions.length > 0 && (
          <ul className={styles.actionList}>
            {summary.recommended_actions.map(action => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        )}

        {summary.capability_coverage.length > 0 && (
          <section className={styles.section}>
            <p className={styles.sectionLabel}>业务能力覆盖</p>
            <ul className={styles.itemList}>
              {summary.capability_coverage.map(item => (
                <li key={item.capability_key || item.business_capability} className={styles.item}>
                  <div className={styles.itemHeader}>
                    <strong>{item.business_capability}</strong>
                    <StatusBadge status={badgeStatus(item.coverage_status)} label={STATUS_LABELS[item.coverage_status]} />
                  </div>
                  {item.technical_entrypoints.length > 0 && (
                    <p className={styles.caption}>{item.technical_entrypoints.join('、')}</p>
                  )}
                  {item.covered_paths.length > 0 && (
                    <p className={styles.caption}>覆盖路径：{item.covered_paths.join('、')}</p>
                  )}
                  {item.gaps.length > 0 && (
                    <p className={styles.warningText}>缺口：{item.gaps.join('、')}</p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {summary.test_files.length > 0 && (
          <section className={styles.section}>
            <p className={styles.sectionLabel}>测试文件维护</p>
            <ul className={styles.itemList}>
              {summary.test_files.map(item => (
                <li key={item.path} className={styles.item}>
                  <div className={styles.itemHeader}>
                    <strong>{item.path}</strong>
                    <StatusBadge status={badgeStatus(item.maintenance_status)} label={STATUS_LABELS[item.maintenance_status]} />
                  </div>
                  {item.covered_capabilities.length > 0 && (
                    <p className={styles.caption}>覆盖能力：{item.covered_capabilities.join('、')}</p>
                  )}
                  {item.invalidation_reasons.length > 0 && (
                    <p className={styles.warningText}>{item.invalidation_reasons.join('、')}</p>
                  )}
                  <p className={styles.caption}>{item.recommendation}</p>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </CardShell>
  )
}
