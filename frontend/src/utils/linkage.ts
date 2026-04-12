import type { OverviewResponse } from '../types/api'

export interface SelectionHighlights {
  capabilityKeys: Set<string>
  journeyNames: Set<string>
  nodeIds: Set<string>
  changeIds: Set<string>
}

export function computeCapabilitySelection(
  capKey: string,
  overview: OverviewResponse,
): SelectionHighlights {
  const cap = overview.capability_map.find(c => c.capability_key === capKey)
  const linkedModules = new Set(cap?.linked_modules ?? [])

  const journeyNames = new Set<string>()
  for (const j of overview.journeys) {
    const text = [j.name, ...(j.steps ?? [])].join(' ').toLowerCase()
    if (cap && text.includes(cap.name.toLowerCase())) {
      journeyNames.add(j.name)
    }
  }

  const nodeIds = new Set<string>(
    overview.architecture_overview.nodes
      .filter(n => linkedModules.has(n.id))
      .map(n => n.id),
  )

  const changeIds = new Set<string>(
    overview.recent_ai_changes
      .filter(c => c.directly_changed_modules.some(m => linkedModules.has(m)))
      .map(c => c.change_id),
  )

  return { capabilityKeys: new Set([capKey]), journeyNames, nodeIds, changeIds }
}

export function computeChangeSelection(
  changeId: string,
  overview: OverviewResponse,
): SelectionHighlights {
  const change = overview.recent_ai_changes.find(c => c.change_id === changeId)
  if (!change) return empty()

  const changedModules = new Set(change.directly_changed_modules)

  const capabilityKeys = new Set<string>(
    overview.capability_map
      .filter(cap => cap.linked_modules.some(m => changedModules.has(m)))
      .map(cap => cap.capability_key),
  )

  const nodeIds = new Set<string>(
    overview.architecture_overview.nodes
      .filter(n => changedModules.has(n.id))
      .map(n => n.id),
  )

  return { capabilityKeys, journeyNames: new Set(), nodeIds, changeIds: new Set([changeId]) }
}

export function computeVerificationSelection(
  moduleName: string,
  overview: OverviewResponse,
): SelectionHighlights {
  const capabilityKeys = new Set<string>(
    overview.capability_map
      .filter(cap => cap.linked_modules.includes(moduleName))
      .map(cap => cap.capability_key),
  )

  const nodeIds = new Set<string>(
    overview.architecture_overview.nodes
      .filter(n => n.id === moduleName)
      .map(n => n.id),
  )

  const changeIds = new Set<string>(
    overview.recent_ai_changes
      .filter(c => c.directly_changed_modules.includes(moduleName))
      .map(c => c.change_id),
  )

  return { capabilityKeys, journeyNames: new Set(), nodeIds, changeIds }
}

function empty(): SelectionHighlights {
  return {
    capabilityKeys: new Set(),
    journeyNames: new Set(),
    nodeIds: new Set(),
    changeIds: new Set(),
  }
}
