import { create } from 'zustand'
import type { OverviewResponse, JobState } from '../types/api'
import {
  computeCapabilitySelection,
  computeChangeSelection,
  computeVerificationSelection,
} from '../utils/linkage'

export type LoadingState = 'idle' | 'loading' | 'rebuilding' | 'error' | 'not_ready'

interface OverviewStore {
  // ─── Data ────────────────────────────────────────────────────────────────
  overview: OverviewResponse | null
  loadingState: LoadingState
  errorMessage: string | null
  activeJobId: string | null
  jobProgress: JobState | null

  // ─── Selection / linkage ─────────────────────────────────────────────────
  selectedCapabilityKey: string | null
  selectedChangeId: string | null
  selectedVerificationModule: string | null
  highlightedCapabilityKeys: Set<string>
  highlightedJourneyNames: Set<string>
  highlightedNodeIds: Set<string>
  highlightedChangeIds: Set<string>

  // ─── Actions ──────────────────────────────────────────────────────────────
  setOverview: (data: OverviewResponse) => void
  setLoadingState: (state: LoadingState, message?: string) => void
  setActiveJob: (jobId: string | null, progress: JobState | null) => void

  selectCapability: (key: string | null) => void
  selectChange: (id: string | null) => void
  selectVerificationModule: (mod: string | null) => void
  clearSelection: () => void
}

const NO_HIGHLIGHTS = {
  highlightedCapabilityKeys: new Set<string>(),
  highlightedJourneyNames: new Set<string>(),
  highlightedNodeIds: new Set<string>(),
  highlightedChangeIds: new Set<string>(),
}

export const useOverviewStore = create<OverviewStore>((set, get) => ({
  overview: null,
  loadingState: 'idle',
  errorMessage: null,
  activeJobId: null,
  jobProgress: null,

  selectedCapabilityKey: null,
  selectedChangeId: null,
  selectedVerificationModule: null,
  ...NO_HIGHLIGHTS,

  setOverview: (data) =>
    set({ overview: data, loadingState: 'idle', errorMessage: null }),

  setLoadingState: (state, message) =>
    set({ loadingState: state, errorMessage: message ?? null }),

  setActiveJob: (jobId, progress) =>
    set({ activeJobId: jobId, jobProgress: progress }),

  selectCapability: (key) => {
    const { overview, selectedCapabilityKey } = get()
    if (!key || key === selectedCapabilityKey) {
      set({ selectedCapabilityKey: null, selectedChangeId: null, selectedVerificationModule: null, ...NO_HIGHLIGHTS })
      return
    }
    const h = overview ? computeCapabilitySelection(key, overview) : null
    set({
      selectedCapabilityKey: key,
      selectedChangeId: null,
      selectedVerificationModule: null,
      highlightedCapabilityKeys: h?.capabilityKeys ?? new Set([key]),
      highlightedJourneyNames: h?.journeyNames ?? new Set(),
      highlightedNodeIds: h?.nodeIds ?? new Set(),
      highlightedChangeIds: h?.changeIds ?? new Set(),
    })
  },

  selectChange: (id) => {
    const { overview, selectedChangeId } = get()
    if (!id || id === selectedChangeId) {
      set({ selectedChangeId: null, selectedCapabilityKey: null, selectedVerificationModule: null, ...NO_HIGHLIGHTS })
      return
    }
    const h = overview ? computeChangeSelection(id, overview) : null
    set({
      selectedChangeId: id,
      selectedCapabilityKey: null,
      selectedVerificationModule: null,
      highlightedCapabilityKeys: h?.capabilityKeys ?? new Set(),
      highlightedJourneyNames: h?.journeyNames ?? new Set(),
      highlightedNodeIds: h?.nodeIds ?? new Set(),
      highlightedChangeIds: h?.changeIds ?? new Set([id]),
    })
  },

  selectVerificationModule: (mod) => {
    const { overview, selectedVerificationModule } = get()
    if (!mod || mod === selectedVerificationModule) {
      set({ selectedVerificationModule: null, selectedCapabilityKey: null, selectedChangeId: null, ...NO_HIGHLIGHTS })
      return
    }
    const h = overview ? computeVerificationSelection(mod, overview) : null
    set({
      selectedVerificationModule: mod,
      selectedCapabilityKey: null,
      selectedChangeId: null,
      highlightedCapabilityKeys: h?.capabilityKeys ?? new Set(),
      highlightedJourneyNames: h?.journeyNames ?? new Set(),
      highlightedNodeIds: h?.nodeIds ?? new Set(),
      highlightedChangeIds: h?.changeIds ?? new Set(),
    })
  },

  clearSelection: () =>
    set({
      selectedCapabilityKey: null,
      selectedChangeId: null,
      selectedVerificationModule: null,
      ...NO_HIGHLIGHTS,
    }),
}))
