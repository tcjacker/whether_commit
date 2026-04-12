import { useOverviewStore } from '../store/useOverviewStore'
import { useOverview } from '../hooks/useOverview'
import { useJobPoller } from '../hooks/useJobPoller'
import { PageHeader } from '../components/layout/PageHeader'
import { DashboardGrid } from '../components/layout/DashboardGrid'
import { ProjectSummaryCard } from '../components/cards/ProjectSummaryCard'
import { CapabilityMapCard } from '../components/cards/CapabilityMapCard'
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
    workspacePath: p.get('workspace_path') ?? undefined,
  }
}

export function OverviewPage() {
  const { repoKey, workspacePath } = getParams()
  const { rebuild } = useOverview(repoKey)
  useJobPoller(repoKey)

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

  const handleRebuild = () => rebuild(workspacePath)

  if (loadingState === 'not_ready') {
    return (
      <div className={styles.page}>
        <PageHeader
          repo={null}
          snapshot={null}
          loadingState={loadingState}
          jobProgress={null}
          onRebuild={handleRebuild}
          onClearSelection={clearSelection}
          hasSelection={false}
        />
        <div className={styles.centered}>
          <EmptyState
            message={`No overview found for "${repoKey}". Trigger a rebuild to analyze the repository.`}
            action={{ label: 'Start Rebuild', onClick: handleRebuild }}
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
          snapshot={null}
          loadingState={loadingState}
          jobProgress={null}
          onRebuild={handleRebuild}
          onClearSelection={clearSelection}
          hasSelection={false}
        />
        <div className={styles.centered}>
          <EmptyState
            message={errorMessage ?? 'An error occurred. Please try rebuilding.'}
            action={{ label: 'Retry Rebuild', onClick: handleRebuild }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <PageHeader
        repo={overview?.repo ?? null}
        snapshot={overview?.snapshot ?? null}
        loadingState={loadingState}
        jobProgress={jobProgress}
        onRebuild={handleRebuild}
        onClearSelection={clearSelection}
        hasSelection={hasSelection}
      />

      <DashboardGrid>
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

        {/* 4 — AI Changes */}
        <AIChangesCard
          changes={overview?.recent_ai_changes ?? []}
          loading={isLoading || isRebuilding}
          highlightedIds={highlightedChangeIds}
          selectedId={selectedChangeId}
          onSelect={selectChange}
        />

        {/* 5 — Architecture (spans full row via CSS) */}
        <ArchitectureCard
          architecture={overview?.architecture_overview ?? { nodes: [], edges: [] }}
          loading={isLoading || isRebuilding}
          highlightedNodeIds={highlightedNodeIds}
        />

        {/* 6 — Verification */}
        <VerificationCard
          status={overview?.verification_status ?? null}
          loading={isLoading || isRebuilding}
          selectedModule={selectedVerificationModule}
          onSelectModule={selectVerificationModule}
        />
      </DashboardGrid>
    </div>
  )
}
