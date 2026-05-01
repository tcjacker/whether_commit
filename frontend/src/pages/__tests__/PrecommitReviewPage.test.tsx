import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PrecommitReviewPage } from '../PrecommitReviewPage'

const snapshot = {
  snapshot_id: 'pr_1',
  review_target: 'staged_only',
  decision: 'needs_review',
  stale: false,
  workspace_changed_outside_target: true,
  summary: { message: 'Pending staged changes require review.', changed_file_count: 1, review_state: 'unreviewed' },
  files: [{
    file_id: 'file_1',
    path: 'backend/schema.py',
    additions: 1,
    deletions: 1,
    risk: { score: 50, band: 'high', reasons: [{ reason_id: 'schema', label: 'Schema changed', weight: 30 }] },
  }],
  hunks: [{
    hunk_id: 'hunk_1',
    hunk_carryover_key: 'hunk_key_1',
    file_id: 'file_1',
    path: 'backend/schema.py',
    old_start: 1,
    old_lines: 1,
    new_start: 1,
    new_lines: 1,
    hunk_fingerprint: 'sha256:hunk',
    lines: [
      { type: 'header', content: '@@ -1 +1 @@' },
      { type: 'remove', content: 'value = 1' },
      { type: 'add', content: 'value = 2' },
    ],
  }],
  signals: [{
    signal_id: 'sig_1',
    kind: 'unreviewed_high_risk_hunk',
    target_type: 'hunk',
    target_id: 'hunk_1',
    severity: 'review',
    status: 'open',
    decision_impact: 'prevents_no_known_blockers',
    evidence_ids: [],
    policy_rule_id: 'high_risk_hunk_unreviewed',
    message: 'backend/schema.py has a high-risk staged hunk that needs review.',
  }],
  queue: [{
    queue_id: 'sig_1',
    item_type: 'signal',
    target_id: 'hunk_1',
    status: 'open',
    message: 'backend/schema.py has a high-risk staged hunk that needs review.',
    priority: 50,
  }],
}

const reviewedSnapshot = {
  ...snapshot,
  decision: 'no_known_blockers',
  workspace_changed_outside_target: false,
  summary: { ...snapshot.summary, review_state: 'reviewed' },
  signals: [{ ...snapshot.signals[0], status: 'reviewed' }],
  queue: [],
}

const api = vi.hoisted(() => ({
  fetchCurrentSnapshot: vi.fn(async () => snapshot),
  rebuildPrecommitReview: vi.fn(async () => snapshot),
  updateHunkReviewState: vi.fn(async () => reviewedSnapshot),
  runVerificationCommand: vi.fn(async () => ({
    run_id: 'run_1',
    status: 'failed',
    exit_code: 1,
    display_status: 'executed',
    target_aligned: true,
  })),
}))

vi.mock('../../api/precommitReview', () => api)

describe('PrecommitReviewPage', () => {
  it('renders review console state and handles hunk review and verification run', async () => {
    render(<PrecommitReviewPage />)

    expect(await screen.findByText('needs review')).toBeInTheDocument()
    expect(screen.getByText('workspace changed outside target')).toBeInTheDocument()
    expect(screen.getAllByText('backend/schema.py').length).toBeGreaterThan(0)
    expect(screen.getAllByText('backend/schema.py has a high-risk staged hunk that needs review.').length).toBeGreaterThan(0)
    expect(screen.getByText('value = 2')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Mark hunk reviewed' }))

    await waitFor(() => expect(api.updateHunkReviewState).toHaveBeenCalledWith('', 'hunk_1', 'reviewed'))
    expect(await screen.findByText('no known blockers')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('verification command'), { target: { value: 'pytest' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run verification' }))

    await waitFor(() => expect(api.runVerificationCommand).toHaveBeenCalledWith('', 'pr_1', 'pytest'))
    expect(await screen.findByText('failed · exit 1 · aligned')).toBeInTheDocument()
  })
})
