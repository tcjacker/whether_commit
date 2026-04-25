import type { CapabilityItem } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { StatusBadge } from '../shared/StatusBadge'
import { EmptyState } from '../shared/EmptyState'
import { zhCount } from '../../i18n'
import styles from './CapabilityMapCard.module.css'

interface Props {
  capabilities: CapabilityItem[]
  loading: boolean
  highlightedKeys: Set<string>
  selectedKey: string | null
  onSelect: (key: string | null) => void
}

type CapabilityDisplay = CapabilityItem & {
  impact_status?: 'unknown' | 'untouched' | 'directly_changed' | 'indirectly_impacted' | 'high_risk_unverified' | string
  impact_reason?: string
  related_themes?: string[]
  verification_status?: 'unknown' | 'verified' | 'unverified' | 'partial' | 'covered' | 'missing' | string
}

const IMPACT_STATUS_LABELS: Record<string, string> = {
  unknown: '影响未知',
  untouched: '未受影响',
  directly_changed: '直接变更',
  indirectly_impacted: '间接受影响',
  high_risk_unverified: '高风险未验证',
}

const VERIFICATION_STATUS_LABELS: Record<string, string> = {
  unknown: '验证未知',
  verified: '已验证',
  unverified: '未验证',
  partial: '部分覆盖',
  covered: '已覆盖',
  missing: '缺失',
}

function zhImpactStatus(status: string | undefined): string {
  if (!status) return '影响未知'
  return IMPACT_STATUS_LABELS[status] ?? status.replace(/_/g, ' ')
}

function zhVerificationStatus(status: string | undefined): string {
  if (!status) return '验证未知'
  return VERIFICATION_STATUS_LABELS[status] ?? status.replace(/_/g, ' ')
}

export function CapabilityMapCard({ capabilities, loading, highlightedKeys, selectedKey, onSelect }: Props) {
  const displayCapabilities = capabilities as CapabilityDisplay[]
  const hasHighlight = highlightedKeys.size > 0

  return (
    <CardShell title="能力地图" subtitle={zhCount(capabilities.length, '项能力')}>
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[1,2,3].map(i => <SkeletonBlock key={i} height={44} />)}
        </div>
      ) : capabilities.length === 0 ? (
        <EmptyState message="尚未识别到能力项，请执行重建以分析代码库。" />
      ) : (
        <ul className={styles.list}>
          {displayCapabilities.map(cap => {
            const isSelected = selectedKey === cap.capability_key
            const dimmed = hasHighlight && !highlightedKeys.has(cap.capability_key)
            const impactStatus = cap.impact_status
            const verificationStatus = cap.verification_status
            const hasNewMeta = Boolean(
              impactStatus ||
              cap.impact_reason ||
              cap.related_themes?.length ||
              verificationStatus,
            )
            return (
              <li
                key={cap.capability_key}
                className={`${styles.item} ${isSelected ? styles.selected : ''} ${dimmed ? styles.dimmed : ''}`}
                onClick={() => onSelect(isSelected ? null : cap.capability_key)}
              >
                <div className={styles.row}>
                  <div className={styles.nameGroup}>
                    <span className={styles.name}>{cap.name}</span>
                    {cap.is_primary_target && (
                      <span className={styles.primaryTag}>主要目标</span>
                    )}
                  </div>
                  <div className={styles.badges}>
                    {hasNewMeta ? (
                      <>
                        <span className={`${styles.pill} ${styles.impactPill}`}>
                          {zhImpactStatus(impactStatus)}
                        </span>
                        {verificationStatus && (
                          <span className={`${styles.pill} ${styles.verificationPill}`}>
                            {zhVerificationStatus(verificationStatus)}
                          </span>
                        )}
                      </>
                    ) : (
                      <StatusBadge status={cap.status} />
                    )}
                  </div>
                </div>
                {cap.impact_reason && (
                  <p className={styles.reason}>{cap.impact_reason}</p>
                )}
                {cap.related_themes?.length ? (
                  <div className={styles.themeRow}>
                    {cap.related_themes.map(theme => (
                      <span key={theme} className={styles.themeTag}>{theme}</span>
                    ))}
                  </div>
                ) : null}
                <div className={styles.meta}>
                  {cap.linked_routes.length > 0 && (
                    <div className={styles.routesBlock}>
                      <span className={styles.metaLabel}>关联入口</span>
                      <span className={styles.routes}>
                        {cap.linked_routes.slice(0, 2).join(', ')}
                        {cap.linked_routes.length > 2 && ` +${cap.linked_routes.length - 2}`}
                      </span>
                    </div>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </CardShell>
  )
}
