import { useEffect, useMemo, useState } from 'react'
import { fetchReviewGraph } from '../api/reviewGraph'
import type {
  ReviewGraphEdge,
  ReviewGraphNode,
  ReviewGraphObjectType,
  ReviewGraphRef,
  ReviewGraphResponse,
} from '../types/api'
import { ApiError } from '../api/client'
import { EmptyState } from '../components/shared/EmptyState'
import { StatusBadge } from '../components/shared/StatusBadge'
import styles from './ReviewGraphPage.module.css'

type LayerMode = 'feature' | 'impact'
type LoadState = 'loading' | 'ready' | 'error' | 'not_ready'

interface ChangeItem {
  title: string
  description: string
}

interface EvidenceItem {
  label: string
  description: string
  badge: 'Case' | 'Suite' | 'Evidence'
}

interface FeatureCardModel {
  feature: ReviewGraphNode
  whatChanged: ChangeItem[]
  coveredCases: EvidenceItem[]
  gaps: string[]
  whyItMatters: string
}

function getParams() {
  const p = new URLSearchParams(window.location.search)
  return {
    repoKey: p.get('repo_key') ?? 'divide_prd_to_ui',
    workspacePath: p.get('workspace_path') ?? '',
  }
}

function mappingStatusLabel(status?: 'missing' | 'invalid') {
  if (status === 'missing') return '映射缺失'
  if (status === 'invalid') return '映射无效'
  return null
}

function humanizeRefKind(kind: ReviewGraphRef['kind']) {
  switch (kind) {
    case 'symbol':
      return '符号'
    case 'file':
      return '文件'
    case 'test_case':
      return 'Case'
    case 'test_suite':
      return 'Suite'
    case 'test_file':
      return 'Suite'
    default:
      return kind
  }
}

function evidenceBadge(node: ReviewGraphNode): EvidenceItem['badge'] {
  if (node.refs.some(ref => ref.kind === 'test_case')) return 'Case'
  if (node.refs.some(ref => ref.kind === 'test_suite' || ref.kind === 'test_file')) return 'Suite'
  return 'Evidence'
}

function relatedNodeIds(featureId: string, edges: ReviewGraphEdge[], nodesById: Map<string, ReviewGraphNode>, type: ReviewGraphObjectType) {
  const ids = new Set<string>()
  for (const edge of edges) {
    if (edge.from === featureId) {
      const other = nodesById.get(edge.to)
      if (other?.type === type) ids.add(other.id)
    }
    if (edge.to === featureId) {
      const other = nodesById.get(edge.from)
      if (other?.type === type) ids.add(other.id)
    }
  }
  return [...ids]
}

function buildFeatureCard(
  feature: ReviewGraphNode,
  edges: ReviewGraphEdge[],
  nodesById: Map<string, ReviewGraphNode>,
): FeatureCardModel {
  const codeNodes = relatedNodeIds(feature.id, edges, nodesById, 'CodeUnit')
    .map(id => nodesById.get(id))
    .filter((node): node is ReviewGraphNode => !!node)

  const evidenceNodes = [
    ...relatedNodeIds(feature.id, edges, nodesById, 'TestUnit'),
    ...relatedNodeIds(feature.id, edges, nodesById, 'EvidenceGroup'),
  ]
    .map(id => nodesById.get(id))
    .filter((node): node is ReviewGraphNode => !!node)

  const whatChanged = codeNodes.length > 0
    ? codeNodes.map(node => ({
        title: node.label,
        description: node.refs[0]?.value ?? 'Mapped code unit',
      }))
    : feature.refs.map(ref => ({
        title: `${feature.label} ${humanizeRefKind(ref.kind)}`,
        description: ref.value,
      }))

  const coveredCases = evidenceNodes.map(node => ({
    label: node.label,
    description: node.refs[0]?.value ?? 'Mapped evidence',
    badge: evidenceBadge(node),
  }))

  const gaps =
    coveredCases.length === 0
      ? ['No case-level evidence is mapped for this feature yet.']
      : feature.match_status === 'expanded' && feature.layers.length === 1
        ? ['This feature appears through impact propagation and still needs direct verification.']
        : []

  return {
    feature,
    whatChanged,
    coveredCases,
    gaps,
    whyItMatters:
      coveredCases.length > 0
        ? `${feature.label} currently anchors ${coveredCases.length} linked evidence items.`
        : `${feature.label} is on the active review path but lacks explicit mapped evidence.`,
  }
}

export function ReviewGraphPage() {
  const { repoKey, workspacePath } = getParams()
  const [loadingState, setLoadingState] = useState<LoadState>('loading')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [graph, setGraph] = useState<ReviewGraphResponse | null>(null)
  const [layerMode, setLayerMode] = useState<LayerMode>('feature')
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | null>(null)

  useEffect(() => {
    setLoadingState('loading')
    fetchReviewGraph(repoKey, workspacePath)
      .then((data) => {
        setGraph(data)
        setLoadingState('ready')
      })
      .catch((error) => {
        if (error instanceof ApiError && error.status === 404) {
          setLoadingState('not_ready')
        } else {
          setLoadingState('error')
          setErrorMessage(error instanceof Error ? error.message : '加载 review graph 失败。')
        }
      })
  }, [repoKey, workspacePath])

  const visibleNodes = useMemo(
    () => (graph?.nodes ?? []).filter(node => node.layers.includes(layerMode)),
    [graph, layerMode],
  )
  const visibleEdges = useMemo(
    () => (graph?.edges ?? []).filter(edge => edge.layers.includes(layerMode)),
    [graph, layerMode],
  )
  const nodesById = useMemo(() => new Map(visibleNodes.map(node => [node.id, node])), [visibleNodes])

  const featureCards = useMemo(() => {
    return visibleNodes
      .filter(node => node.type === 'FeatureContainer')
      .map(node => buildFeatureCard(node, visibleEdges, nodesById))
  }, [visibleNodes, visibleEdges, nodesById])

  useEffect(() => {
    if (featureCards.length === 0) {
      setSelectedFeatureId(null)
      return
    }
    if (!selectedFeatureId || !featureCards.some(card => card.feature.id === selectedFeatureId)) {
      setSelectedFeatureId(featureCards[0].feature.id)
    }
  }, [featureCards, selectedFeatureId])

  const impactOnlyFeatures = (graph?.nodes ?? []).filter(
    node => node.type === 'FeatureContainer' && node.layers.length === 1 && node.layers[0] === 'impact',
  )
  const hasNoPendingChanges =
    loadingState === 'ready' &&
    (graph?.summary.direct_feature_count ?? 0) === 0 &&
    (graph?.summary.impacted_feature_count ?? 0) === 0 &&
    (graph?.nodes.length ?? 0) === 0 &&
    (graph?.summary.title ?? '').toLowerCase().includes('no pending changes')

  if (loadingState === 'not_ready') {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Change Review</p>
            <h1 className={styles.title}>变更评审工作台</h1>
          </div>
        </header>
        <div className={styles.centered}>
          <EmptyState message={`未找到仓库“${repoKey}”的 review graph 数据，请先执行后端重建。`} />
        </div>
      </div>
    )
  }

  if (loadingState === 'error') {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Change Review</p>
            <h1 className={styles.title}>变更评审工作台</h1>
          </div>
        </header>
        <div className={styles.centered}>
          <EmptyState message={errorMessage ?? '加载 review graph 失败。'} />
        </div>
      </div>
    )
  }

  const overviewParams = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath.trim()) {
    overviewParams.set('workspace_path', workspacePath.trim())
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Change Review</p>
          <h1 className={styles.title}>变更评审工作台</h1>
          <p className={styles.subtitle}>{graph?.summary.title ?? 'Loading review graph...'}</p>
        </div>
        <a className={styles.backLink} href={`/?${overviewParams.toString()}`}>
          返回总览
        </a>
      </header>

      <section className={styles.summaryBar}>
        <Metric label="Direct Features" value={graph?.summary.direct_feature_count ?? 0} />
        <Metric label="Covered Cases" value={featureCards.reduce((sum, card) => sum + card.coveredCases.length, 0)} />
        <Metric label="Impacted Features" value={graph?.summary.impacted_feature_count ?? 0} />
        <Metric label="Gaps" value={graph?.summary.verification_gap_count ?? 0} />
        {mappingStatusLabel(graph?.summary.mapping_status) && (
          <div className={styles.mappingState}>
            <StatusBadge status="warning" label={mappingStatusLabel(graph?.summary.mapping_status) ?? undefined} />
          </div>
        )}
      </section>

      <section className={styles.workspace}>
        {hasNoPendingChanges ? (
          <div className={styles.centered}>
            <EmptyState message="当前工作区没有待分析变更。" />
          </div>
        ) : (
          <>
            <div className={styles.primaryColumn}>
              {loadingState === 'loading' ? (
            <div className={styles.loadingState}>正在加载 review graph…</div>
          ) : (
            featureCards.map(card => {
              const isSelected = selectedFeatureId === card.feature.id
              return (
                <article
                  key={card.feature.id}
                  className={`${styles.featureCard} ${isSelected ? styles.featureCardSelected : ''}`}
                >
                  <div className={styles.featureCardHeader}>
                    <button
                      className={styles.featureSelectButton}
                      onClick={() => setSelectedFeatureId(card.feature.id)}
                    >
                      <span className={styles.featureTitle}>{card.feature.label}</span>
                    </button>
                    <div className={styles.featureBadges}>
                      <StatusBadge
                        status={card.feature.match_status === 'direct' ? 'stable' : 'warning'}
                        label={card.feature.match_status === 'direct' ? 'Direct change' : 'Impact only'}
                      />
                      {isSelected && <StatusBadge status="running" label="Selected" />}
                    </div>
                  </div>

                  <div className={styles.snapshotBox}>
                    <span className={styles.snapshotLabel}>Coverage Snapshot</span>
                    <strong>{card.coveredCases.length} covered</strong>
                    <span>{card.gaps.length} gap</span>
                  </div>

                  <div className={styles.featureGrid}>
                    <section className={styles.featurePanel}>
                      <div className={styles.panelHeader}>
                        <h2>What Changed</h2>
                        <span>{card.whatChanged.length} items</span>
                      </div>
                      <ul className={styles.changeList}>
                        {card.whatChanged.map(item => (
                          <li key={`${card.feature.id}:${item.title}`} className={styles.changeItem}>
                            <strong>{item.title}</strong>
                            <span>{item.description}</span>
                          </li>
                        ))}
                      </ul>
                    </section>

                    <section className={styles.featurePanel}>
                      <div className={styles.panelHeader}>
                        <h2>Covered Cases</h2>
                        <span>{card.coveredCases.length}</span>
                      </div>
                      {card.coveredCases.length > 0 ? (
                        <ul className={styles.caseList}>
                          {card.coveredCases.map(item => (
                            <li key={`${card.feature.id}:${item.label}`} className={styles.caseItem}>
                              <div className={styles.caseHead}>
                                <strong>{item.label}</strong>
                                <span className={styles.caseBadge}>{item.badge}</span>
                              </div>
                              <span>{item.description}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className={styles.emptyInline}>No mapped cases yet.</p>
                      )}
                    </section>

                    <div className={styles.sideStack}>
                      <section className={styles.featurePanel}>
                        <div className={styles.panelHeader}>
                          <h2>Gaps</h2>
                        </div>
                        {card.gaps.length > 0 ? (
                          <ul className={styles.gapList}>
                            {card.gaps.map(gap => (
                              <li key={`${card.feature.id}:${gap}`} className={styles.gapItem}>{gap}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className={styles.emptyInline}>No explicit gaps are mapped for this feature.</p>
                        )}
                      </section>

                      <section className={styles.whyPanel}>
                        <div className={styles.panelHeader}>
                          <h2>Why It Matters</h2>
                          <span>collapsed</span>
                        </div>
                        <p>{card.whyItMatters}</p>
                      </section>
                    </div>
                  </div>
                </article>
              )
            })
          )}
            </div>
            <aside className={styles.secondaryColumn}>
              <section className={styles.sideCard}>
                <div className={styles.sideCardHeader}>
                  <h2>Coverage Matrix</h2>
                </div>
                <div className={styles.matrixList}>
                  {featureCards.map(card => (
                    <button
                      key={`matrix:${card.feature.id}`}
                      className={`${styles.matrixItem} ${selectedFeatureId === card.feature.id ? styles.matrixItemActive : ''}`}
                      onClick={() => setSelectedFeatureId(card.feature.id)}
                    >
                      <span>{card.feature.label}</span>
                      <span className={styles.matrixCount}>
                        {card.coveredCases.length > 0 ? `${card.coveredCases.length} cases` : '0 cases'}
                      </span>
                    </button>
                  ))}
                </div>
              </section>

              <section className={styles.sideCard}>
                <div className={styles.sideCardHeader}>
                  <h2>Impact Analysis</h2>
                  <button
                    className={styles.impactButton}
                    onClick={() => setLayerMode(layerMode === 'feature' ? 'impact' : 'feature')}
                  >
                    {layerMode === 'feature' ? 'Show impact analysis' : 'Back to primary review'}
                  </button>
                </div>
                {layerMode === 'impact' ? (
                  impactOnlyFeatures.length > 0 ? (
                    <div className={styles.impactList}>
                      {impactOnlyFeatures.map(node => (
                        <div key={node.id} className={styles.impactItem}>
                          <strong>{node.label}</strong>
                          <span>{node.refs[0]?.value ?? 'Impact-only feature'}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className={styles.emptyInline}>No impact-only features in this graph.</p>
                  )
                ) : (
                  <p className={styles.sideNote}>
                    影响分析留在次级区域，需要时再展开，不与主阅读顺序竞争。
                  </p>
                )}
              </section>

              {graph && graph.unresolved_refs.length > 0 && (
                <section className={styles.sideCard}>
                  <div className={styles.sideCardHeader}>
                    <h2>Unresolved refs</h2>
                  </div>
                  <div className={styles.unresolvedList}>
                    {graph.unresolved_refs.slice(0, 12).map(ref => (
                      <div key={ref} className={styles.unresolvedItem}>{ref}</div>
                    ))}
                    {graph.unresolved_refs.length > 12 && (
                      <div className={styles.unresolvedMore}>+ {graph.unresolved_refs.length - 12} more</div>
                    )}
                  </div>
                </section>
              )}
            </aside>
          </>
        )}
      </section>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className={styles.metric}>
      <span className={styles.metricLabel}>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
