import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from '../../App'

const reviewGraphFixture = {
  version: 'v1',
  change_id: 'chg-123',
  summary: {
    title: 'Orders change review',
    direct_feature_count: 2,
    impacted_feature_count: 1,
    verification_gap_count: 1,
  },
  nodes: [
    {
      id: 'feature.orders_api',
      type: 'FeatureContainer',
      label: 'OrdersApi',
      match_status: 'direct',
      layers: ['feature', 'impact'],
      refs: [{ kind: 'file', value: 'backend/app/api/orders.py' }],
    },
    {
      id: 'code.create_order',
      type: 'CodeUnit',
      label: 'create_order',
      match_status: 'direct',
      layers: ['feature', 'impact'],
      refs: [{ kind: 'symbol', value: 'backend.app.services.order_service.create_order' }],
    },
    {
      id: 'test.orders_api',
      type: 'TestUnit',
      label: 'Orders API tests',
      match_status: 'expanded',
      layers: ['feature', 'impact'],
      refs: [{ kind: 'test_file', value: 'backend/tests/api/test_orders.py' }],
    },
    {
      id: 'feature.merchant_status_api',
      type: 'FeatureContainer',
      label: 'MerchantStatusApi',
      match_status: 'expanded',
      layers: ['impact'],
      refs: [{ kind: 'file', value: 'backend/app/api/merchant_status.py' }],
    },
  ],
  edges: [
    { from: 'feature.orders_api', to: 'code.create_order', type: 'owns', layers: ['feature', 'impact'] },
    { from: 'test.orders_api', to: 'feature.orders_api', type: 'verifies_primary', layers: ['feature', 'impact'] },
    { from: 'code.create_order', to: 'feature.merchant_status_api', type: 'impacts', layers: ['impact'] },
  ],
  unresolved_refs: [],
}

const noChangesFixture = {
  version: 'v1',
  change_id: 'chg_none',
  summary: {
    title: 'No pending changes',
    direct_feature_count: 0,
    impacted_feature_count: 0,
    verification_gap_count: 0,
  },
  nodes: [],
  edges: [],
  unresolved_refs: [],
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  window.history.replaceState({}, '', '/')
})

describe('ReviewGraphPage', () => {
  it('renders review graph workspace on the dedicated route', async () => {
    window.history.pushState({}, '', '/review-graph?repo_key=demo&workspace_path=%2Ftmp%2Fdemo')
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(reviewGraphFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<App />)

    expect(screen.getByText('变更评审工作台')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Orders change review')).toBeInTheDocument())
    expect(fetchSpy).toHaveBeenCalledWith('/api/changes/review-graph/latest?repo_key=demo&workspace_path=%2Ftmp%2Fdemo', expect.anything())
    expect(screen.getByText('What Changed')).toBeInTheDocument()
    expect(screen.getAllByText('Covered Cases').length).toBeGreaterThan(0)
    expect(screen.getByText('Coverage Matrix')).toBeInTheDocument()
    expect(screen.getAllByText('OrdersApi').length).toBeGreaterThan(0)
    expect(screen.getByText('create_order')).toBeInTheDocument()
    expect(screen.getByText('Orders API tests')).toBeInTheDocument()
    expect(screen.queryByText('MerchantStatusApi')).not.toBeInTheDocument()
  })

  it('updates the selected feature card when selecting a different feature', async () => {
    window.history.pushState({}, '', '/review-graph?repo_key=demo')
    vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(reviewGraphFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<App />)

    await waitFor(() => expect(screen.getByText('Orders change review')).toBeInTheDocument())
    fireEvent.click(screen.getAllByRole('button', { name: /OrdersApi/i })[0])

    expect(screen.getByText('Selected')).toBeInTheDocument()
    expect(screen.getByText('backend.app.services.order_service.create_order')).toBeInTheDocument()
    expect(screen.getByText('No explicit gaps are mapped for this feature.')).toBeInTheDocument()
  })

  it('reveals impact-only nodes from the secondary impact analysis control', async () => {
    window.history.pushState({}, '', '/review-graph?repo_key=demo')
    vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(reviewGraphFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<App />)

    await waitFor(() => expect(screen.getByText('Orders change review')).toBeInTheDocument())
    expect(screen.queryByText('MerchantStatusApi')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Show impact analysis' }))

    expect(screen.getAllByText('MerchantStatusApi').length).toBeGreaterThan(0)
  })

  it('shows an explicit no-pending-changes state instead of an empty workspace', async () => {
    window.history.pushState({}, '', '/review-graph?repo_key=demo&workspace_path=%2Ftmp%2Fdemo')
    vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(noChangesFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(<App />)

    await waitFor(() => expect(screen.getByText('No pending changes')).toBeInTheDocument())
    expect(screen.getByText('当前工作区没有待分析变更。')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '返回总览' })).toHaveAttribute(
      'href',
      '/?repo_key=demo&workspace_path=%2Ftmp%2Fdemo',
    )
  })
})
