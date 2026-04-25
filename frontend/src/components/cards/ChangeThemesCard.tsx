import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { EmptyState } from '../shared/EmptyState'
import { StatusBadge } from '../shared/StatusBadge'
import { zhChangeTitle } from '../../i18n'
import { buildReviewGraphUrl } from '../../utils/reviewGraph'
import type {
  AgentHarnessChangeTheme,
  AgentHarnessStatus,
  RecentAIChange,
} from '../../types/api'
import styles from './ChangeThemesCard.module.css'

interface Props {
  themes: AgentHarnessChangeTheme[]
  legacyChanges: RecentAIChange[]
  loading: boolean
  selectedChangeId: string | null
  highlightedChangeIds: Set<string>
  agentHarnessStatus: AgentHarnessStatus | null
  agentHarnessMetadata: Record<string, unknown>
  onSelectChange: (id: string | null) => void
  repoKey: string
}

interface DisplayTheme {
  theme_key: string
  name: string
  summary: string
  capability_keys: string[]
  change_ids: string[]
}

function synthesizeLegacyThemes(legacyChanges: RecentAIChange[]): DisplayTheme[] {
  return legacyChanges.map(change => ({
    theme_key: change.change_id,
    name: zhChangeTitle(change.change_title),
    summary: change.summary,
    capability_keys: [],
    change_ids: [change.change_id],
  }))
}

function zhHarnessSource(status: AgentHarnessStatus | null, isLegacyFallback: boolean): string {
  if (isLegacyFallback) return '兼容 legacy'
  switch (status) {
    case 'accepted':
      return 'Agent 已接管'
    case 'fallback':
      return 'Agent 已降级'
    case 'timeout':
      return 'Agent 超时降级'
    case 'validation_failed':
      return 'Agent 校验失败'
    case 'budget_exceeded':
      return 'Agent 预算超限'
    default:
      return '兼容层'
  }
}

export function ChangeThemesCard({
  themes,
  legacyChanges,
  loading,
  selectedChangeId,
  highlightedChangeIds,
  agentHarnessStatus,
  agentHarnessMetadata,
  onSelectChange,
  repoKey,
}: Props) {
  const hasHighlight = highlightedChangeIds.size > 0
  const displayThemes = themes.length > 0 ? themes : synthesizeLegacyThemes(legacyChanges)
  const isLegacyFallback = themes.length === 0 && legacyChanges.length > 0
  const roundsUsed = typeof agentHarnessMetadata.rounds_used === 'number'
    ? ` · ${agentHarnessMetadata.rounds_used} 轮`
    : ''

  return (
    <CardShell
      title="变更主题"
      subtitle={displayThemes.length ? `${displayThemes.length} 个主题${roundsUsed}` : undefined}
      badge={<StatusBadge status={agentHarnessStatus ?? 'unknown'} label={zhHarnessSource(agentHarnessStatus, isLegacyFallback)} />}
    >
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[1, 2].map(i => <SkeletonBlock key={i} height={88} />)}
        </div>
      ) : displayThemes.length === 0 ? (
        <EmptyState message="当前没有可展示的变更主题。" />
      ) : (
        <>
          {isLegacyFallback && (
            <div className={styles.fallbackNote}>
              当前结果尚未生成主题聚合，已按原始变更记录兼容展示。
            </div>
          )}
          <ul className={styles.list}>
            {displayThemes.map(theme => {
              const isSelected = selectedChangeId ? theme.change_ids.includes(selectedChangeId) : false
              const dimmed = hasHighlight && !theme.change_ids.some(id => highlightedChangeIds.has(id))
              const capabilityCount = theme.capability_keys.length

              return (
                <li
                  key={theme.theme_key}
                  className={`${styles.item} ${isSelected ? styles.selected : ''} ${dimmed ? styles.dimmed : ''}`}
                  onClick={() => onSelectChange(theme.change_ids[0] ?? null)}
                >
                  <div className={styles.header}>
                    <div className={styles.titleGroup}>
                      <span className={styles.title}>{theme.name || theme.theme_key}</span>
                      <span className={styles.key}>{theme.theme_key}</span>
                    </div>
                    <div className={styles.metaPills}>
                      <span className={styles.pill}>{capabilityCount} 个能力</span>
                      <span className={styles.pill}>{theme.change_ids.length} 组修改</span>
                    </div>
                  </div>

                  {theme.summary && <p className={styles.summary}>{theme.summary}</p>}

                  {theme.capability_keys.length > 0 && (
                    <div className={styles.tags}>
                      {theme.capability_keys.slice(0, 4).map(key => (
                        <span key={key} className={styles.tag}>{key}</span>
                      ))}
                      {theme.capability_keys.length > 4 && (
                        <span className={styles.tag}>+{theme.capability_keys.length - 4}</span>
                      )}
                    </div>
                  )}

                  {isSelected && (
                    <div className={styles.detail}>
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}>主题编号</span>
                        <span className={styles.detailValue}>{theme.theme_key}</span>
                      </div>
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}>关联修改</span>
                        <span className={styles.detailValue}>{theme.change_ids.join(', ') || '—'}</span>
                      </div>
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}>关联能力</span>
                        <span className={styles.detailValue}>
                          {theme.capability_keys.length > 0 ? theme.capability_keys.join(', ') : '—'}
                        </span>
                      </div>
                      <div className={styles.detailActions}>
                        <a
                          className={styles.reviewLink}
                          href={buildReviewGraphUrl(repoKey, theme.change_ids[0] ?? undefined)}
                          onClick={e => e.stopPropagation()}
                        >
                          Open Review Graph
                        </a>
                      </div>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </>
      )}
    </CardShell>
  )
}
