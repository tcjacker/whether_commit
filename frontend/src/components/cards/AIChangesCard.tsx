import { useState } from 'react'
import type { RecentAIChange } from '../../types/api'
import { CardShell } from '../shared/CardShell'
import { SkeletonBlock } from '../shared/SkeletonBlock'
import { RiskBar } from '../shared/RiskBar'
import { EmptyState } from '../shared/EmptyState'
import { DiffViewer } from '../diff/DiffViewer'
import { zhChangeTitle, zhChangeType, zhConfidence } from '../../i18n'
import { buildReviewGraphUrl } from '../../utils/reviewGraph'
import styles from './AIChangesCard.module.css'

interface Props {
  changes: RecentAIChange[]
  loading: boolean
  highlightedIds: Set<string>
  selectedId: string | null
  onSelect: (id: string | null) => void
  repoKey: string
  legacyMode?: boolean
}

export function AIChangesCard({ changes, loading, highlightedIds, selectedId, onSelect, repoKey, legacyMode = false }: Props) {
  const hasHighlight = highlightedIds.size > 0
  const [diffFile, setDiffFile] = useState<string | null>(null)
  const title = legacyMode ? '原始变更记录（兼容层）' : '最近 AI 变更'
  const subtitle = legacyMode
    ? (changes.length ? `${changes.length} 组原始记录，供兼容旧视图使用` : '供兼容旧视图与调试使用')
    : (changes.length ? `${changes.length} 组变更` : undefined)

  return (
    <CardShell title={title} subtitle={subtitle}>
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[1, 2].map(i => <SkeletonBlock key={i} height={72} />)}
        </div>
      ) : changes.length === 0 ? (
        <EmptyState message={legacyMode ? '当前没有可展示的原始变更记录。' : '当前工作区未检测到待分析的变更。'} />
      ) : (
        <ul className={styles.list}>
          {changes.map(c => {
            const isSelected = selectedId === c.change_id
            const dimmed = hasHighlight && !highlightedIds.has(c.change_id)

            const riskScore = c.risk_factors.length > 0
              ? Math.min(1, c.risk_factors.length / 5)
              : 0.1

            return (
              <li
                key={c.change_id}
                className={`${styles.item} ${isSelected ? styles.selected : ''} ${dimmed ? styles.dimmed : ''}`}
                onClick={() => onSelect(isSelected ? null : c.change_id)}
              >
                <div className={styles.header}>
                  <span className={styles.title}>{zhChangeTitle(c.change_title)}</span>
                  <span className={`${styles.confidence} ${styles[c.confidence] ?? ''}`}>
                    {zhConfidence(c.confidence)}
                  </span>
                </div>

                {c.coherence === 'mixed' && c.coherence_groups && c.coherence_groups.length > 0 && (
                  <div className={styles.coherenceWarning}>
                    混合变更：涉及 {c.coherence_groups.length} 个不相关区域：{c.coherence_groups.join(', ')}
                  </div>
                )}

                {c.summary && <p className={styles.summary}>{c.summary}</p>}

                {c.change_types.length > 0 && (
                  <div className={styles.tags}>
                    {c.change_types.map(t => (
                      <span key={t} className={styles.tag}>{zhChangeType(t)}</span>
                    ))}
                  </div>
                )}

                <div className={styles.footer}>
                  <span className={styles.files}>
                    {c.changed_files.length} 个文件
                  </span>
                  <RiskBar score={riskScore} />
                </div>

                {isSelected && (
                  <div className={styles.detail}>
                    {c.change_intent && (
                      <div className={styles.intentBox}>
                        <span className={styles.intentLabel}>变更意图</span>
                        {c.change_intent}
                      </div>
                    )}

                    {c.changed_files.length > 0 && (
                      <>
                        <p className={styles.detailLabel}>变更文件</p>
                        <ul className={styles.fileList}>
                          {c.changed_files.map((f, i) => (
                            <li key={i}>
                              <button
                                className={styles.fileLink}
                                onClick={e => { e.stopPropagation(); setDiffFile(f) }}
                              >
                                {f}
                              </button>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}

                    {c.affected_capabilities.length > 0 && (
                      <>
                        <p className={styles.detailLabel} style={{ marginTop: 8 }}>影响能力</p>
                        <p className={styles.summary}>{c.affected_capabilities.join('、')}</p>
                      </>
                    )}

                    {c.technical_entrypoints.length > 0 && (
                      <>
                        <p className={styles.detailLabel} style={{ marginTop: 8 }}>技术入口</p>
                        <p className={styles.summary}>{c.technical_entrypoints.join('、')}</p>
                      </>
                    )}

                    {c.risk_factors.length > 0 && (
                      <>
                        <p className={styles.detailLabel} style={{ marginTop: 8 }}>风险因素</p>
                        <ul className={styles.riskList}>
                          {c.risk_factors.map((r, i) => (
                            <li key={i}>⚠ {r}</li>
                          ))}
                        </ul>
                      </>
                    )}
                    {c.review_recommendations.length > 0 && (
                      <>
                        <p className={styles.detailLabel} style={{ marginTop: 8 }}>建议关注</p>
                        <ul className={styles.riskList}>
                          {c.review_recommendations.map((r, i) => (
                            <li key={i}>→ {r}</li>
                          ))}
                        </ul>
                      </>
                    )}
                    <div className={styles.actions}>
                      <a
                        className={styles.reviewLink}
                        href={buildReviewGraphUrl(repoKey, c.change_id)}
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
      )}

      {diffFile && (
        <DiffViewer
          repoKey={repoKey}
          filePath={diffFile}
          onClose={() => setDiffFile(null)}
        />
      )}
    </CardShell>
  )
}
