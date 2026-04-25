import { useEffect, useState } from 'react'
import { useOverviewStore } from '../store/useOverviewStore'
import { useOverview } from '../hooks/useOverview'
import { useJobPoller } from '../hooks/useJobPoller'
import { PageHeader } from '../components/layout/PageHeader'
import { DashboardGrid } from '../components/layout/DashboardGrid'
import { ProjectSummaryCard } from '../components/cards/ProjectSummaryCard'
import { ChangeRiskSummaryCard } from '../components/cards/ChangeRiskSummaryCard'
import { TestAssetSummaryCard } from '../components/cards/TestAssetSummaryCard'
import { ProjectStructureChangeCard } from '../components/cards/ProjectStructureChangeCard'
import { CapabilityMapCard } from '../components/cards/CapabilityMapCard'
import { ChangeThemesCard } from '../components/cards/ChangeThemesCard'
import { UserJourneysCard } from '../components/cards/UserJourneysCard'
import { ArchitectureCard } from '../components/cards/ArchitectureCard'
import { AIChangesCard } from '../components/cards/AIChangesCard'
import { VerificationCard } from '../components/cards/VerificationCard'
import { EmptyState } from '../components/shared/EmptyState'
import styles from './OverviewPage.module.css'

// ── Repo config ──────────────────────────────────────────────────────────────
// Reads from URL search params: ?repo_key=xxx&workspace_path=xxx
function getParams() {
  const p = new URLSearchParams(window.location.search)
  return {
    repoKey: p.get('repo_key') ?? 'divide_prd_to_ui',
    workspacePath: p.get('workspace_path') ?? '',
  }
}

export function OverviewPage() {
  const { repoKey, workspacePath: initialWorkspacePath } = getParams()
  const [workspacePath, setWorkspacePath] = useState(initialWorkspacePath)
  const { rebuild } = useOverview(repoKey, workspacePath)
  useJobPoller(repoKey)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    params.set('repo_key', repoKey)
    if (workspacePath.trim()) {
      params.set('workspace_path', workspacePath.trim())
    } else {
      params.delete('workspace_path')
    }
    const next = `${window.location.pathname}?${params.toString()}`
    window.history.replaceState({}, '', next)
  }, [repoKey, workspacePath])

  const {
    overview,
    loadingState,
    errorMessage,
    jobProgress,
    selectedCapabilityKey,
    selectedChangeId,
    selectedVerificationModule,
    highlightedCapabilityKeys,
    highlightedJourneyNames,
    highlightedNodeIds,
    highlightedChangeIds,
    selectCapability,
    selectChange,
    selectVerificationModule,
    clearSelection,
  } = useOverviewStore()

  const isLoading = loadingState === 'loading'
  const isRebuilding = loadingState === 'rebuilding'
  const hasSelection = !!(selectedCapabilityKey || selectedChangeId || selectedVerificationModule)
  const changeThemes = overview?.change_themes ?? []
  const hasThemeLayer = changeThemes.length > 0
  const hasNoPendingChanges = loadingState === 'idle' && overview?.snapshot?.has_pending_changes === false

  const handleRebuild = () => rebuild(workspacePath)

  if (loadingState === 'not_ready') {
    return (
      <div className={styles.page}>
        <PageHeader
          repo={null}
          repoKey={repoKey}
          workspacePath={workspacePath}
          snapshot={null}
          loadingState={loadingState}
          jobProgress={null}
          onRebuild={handleRebuild}
          onWorkspacePathChange={setWorkspacePath}
          onClearSelection={clearSelection}
          hasSelection={false}
        />
        <div className={styles.centered}>
          <EmptyState
            message={`未找到仓库“${repoKey}”的总览数据，请先触发重建以分析仓库。`}
            action={{ label: '开始重建', onClick: handleRebuild }}
          />
        </div>
      </div>
    )
  }

  if (loadingState === 'error') {
    return (
      <div className={styles.page}>
        <PageHeader
          repo={null}
          repoKey={repoKey}
          workspacePath={workspacePath}
          snapshot={null}
          loadingState={loadingState}
          jobProgress={null}
          onRebuild={handleRebuild}
          onWorkspacePathChange={setWorkspacePath}
          onClearSelection={clearSelection}
          hasSelection={false}
        />
        <div className={styles.centered}>
          <EmptyState
            message={errorMessage ?? '发生错误，请重新执行重建。'}
            action={{ label: '重新重建', onClick: handleRebuild }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <PageHeader
        repo={overview?.repo ?? null}
        repoKey={repoKey}
        workspacePath={workspacePath}
        snapshot={overview?.snapshot ?? null}
        loadingState={loadingState}
        jobProgress={jobProgress}
        onRebuild={handleRebuild}
        onWorkspacePathChange={setWorkspacePath}
        onClearSelection={clearSelection}
        hasSelection={hasSelection}
      />

      {hasNoPendingChanges && (
        <section className={styles.noticeBar} aria-label="workspace-clean-notice">
          <strong>当前 workspace 无待分析变更</strong>
          <span>当前工作区与基线提交一致，Change Review 将显示为空。</span>
        </section>
      )}

      <DashboardGrid>
        <ChangeRiskSummaryCard
          summary={overview?.change_risk_summary ?? null}
          loading={isLoading || isRebuilding}
        />

        <TestAssetSummaryCard
          summary={overview?.test_asset_summary ?? null}
          loading={isLoading || isRebuilding}
        />

        <ProjectStructureChangeCard
          changes={overview?.recent_ai_changes ?? []}
          fileReviewSummaries={overview?.file_review_summaries ?? []}
          changeRiskSummary={overview?.change_risk_summary ?? null}
          testAssetSummary={overview?.test_asset_summary ?? null}
          loading={isLoading || isRebuilding}
        />

        {/* 1 — Project Summary */}
        <ProjectSummaryCard
          summary={overview?.project_summary ?? null}
          loading={isLoading || isRebuilding}
        />

        {/* 2 — Capability Map */}
        <CapabilityMapCard
          capabilities={overview?.capability_map ?? []}
          loading={isLoading || isRebuilding}
          highlightedKeys={highlightedCapabilityKeys}
          selectedKey={selectedCapabilityKey}
          onSelect={selectCapability}
        />

        {/* 3 — User Journeys */}
        <UserJourneysCard
          journeys={overview?.journeys ?? []}
          loading={isLoading || isRebuilding}
          highlightedNames={highlightedJourneyNames}
        />

        {/* 4 — Change Themes */}
        <ChangeThemesCard
          themes={changeThemes}
          legacyChanges={overview?.recent_ai_changes ?? []}
          loading={isLoading || isRebuilding}
          selectedChangeId={selectedChangeId}
          highlightedChangeIds={highlightedChangeIds}
          agentHarnessStatus={overview?.agent_harness_status ?? null}
          agentHarnessMetadata={overview?.agent_harness_metadata ?? {}}
          onSelectChange={selectChange}
          repoKey={repoKey}
        />

        {/* 5 — Architecture (spans full row via CSS) */}
        <ArchitectureCard
          architecture={overview?.architecture_overview ?? { nodes: [], edges: [] }}
          loading={isLoading || isRebuilding}
          highlightedNodeIds={highlightedNodeIds}
        />

        {/* 6 — AI Changes */}
        <AIChangesCard
          changes={overview?.recent_ai_changes ?? []}
          loading={isLoading || isRebuilding}
          highlightedIds={highlightedChangeIds}
          selectedId={selectedChangeId}
          onSelect={selectChange}
          repoKey={repoKey}
          legacyMode={hasThemeLayer}
        />

        {/* 7 — Verification */}
        <VerificationCard
          status={overview?.verification_status ?? null}
          loading={isLoading || isRebuilding}
          selectedModule={selectedVerificationModule}
          onSelectModule={selectVerificationModule}
          repoKey={repoKey}
          workspacePath={workspacePath}
        />
      </DashboardGrid>
    </div>
  )
}
