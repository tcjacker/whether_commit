import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { AIChangesCard } from '../AIChangesCard'
import { ChangeThemesCard } from '../ChangeThemesCard'
import type { RecentAIChange, AgentHarnessChangeTheme } from '../../../types/api'

afterEach(() => {
  cleanup()
})

const changeFixture: RecentAIChange = {
  change_id: 'chg-123',
  change_title: 'orders flow',
  summary: 'orders and retry flow changed',
  affected_capabilities: [],
  technical_entrypoints: [],
  changed_files: ['backend/app/api/orders.py'],
  changed_symbols: [],
  changed_routes: [],
  changed_schemas: [],
  changed_jobs: [],
  change_types: ['logic'],
  directly_changed_modules: [],
  transitively_affected_modules: [],
  affected_entrypoints: [],
  affected_data_objects: [],
  why_impacted: '',
  risk_factors: [],
  review_recommendations: [],
  linked_tests: [],
  verification_coverage: 'partial',
  confidence: 'medium',
  change_intent: '',
  coherence: 'focused',
  coherence_groups: [],
}

const themeFixture: AgentHarnessChangeTheme = {
  theme_key: 'theme.orders',
  name: 'Orders flow',
  summary: 'focus on orders path',
  capability_keys: ['orders.create'],
  change_ids: ['chg-123'],
}

describe('change entry links', () => {
  it('renders a review graph link from AI changes detail', () => {
    render(
      <AIChangesCard
        changes={[changeFixture]}
        loading={false}
        highlightedIds={new Set()}
        selectedId="chg-123"
        onSelect={() => {}}
        repoKey="demo"
      />,
    )

    const link = screen.getByRole('link', { name: 'Open Review Graph' })
    expect(link).toHaveAttribute('href', '/review-graph?repo_key=demo&change_id=chg-123')
  })

  it('renders a review graph link from change theme detail', () => {
    render(
      <ChangeThemesCard
        themes={[themeFixture]}
        legacyChanges={[]}
        loading={false}
        selectedChangeId="chg-123"
        highlightedChangeIds={new Set()}
        agentHarnessStatus="accepted"
        agentHarnessMetadata={{}}
        onSelectChange={() => {}}
        repoKey="demo"
      />,
    )

    const link = screen.getByRole('link', { name: 'Open Review Graph' })
    expect(link).toHaveAttribute('href', '/review-graph?repo_key=demo&change_id=chg-123')
  })
})
