import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { FileEvidencePanel } from '../FileEvidencePanel'
import type { ChangedFileDetail } from '../../../types/api'

const duplicateReasons = [
  'Public API/type/config surface changed.',
  'Agent claim conflicts with fact-layer evidence.',
  'Test evidence is unknown.',
  'Large file-level diff.',
]

function detailWithDuplicateHunkChecks(): ChangedFileDetail {
  return {
    file: {
      file_id: 'cf_1',
      path: 'backend/app/schemas/assessment.py',
      old_path: null,
      status: 'modified',
      additions: 82,
      deletions: 0,
      risk_level: 'low',
      coverage_status: 'covered',
      review_status: 'unreviewed',
      agent_sources: ['codex'],
      diff_fingerprint: 'sha256:file',
      highest_hunk_priority: 100,
      mismatch_count: 1,
      weakest_test_evidence_grade: 'unknown',
    },
    diff_hunks: [],
    changed_symbols: ['A', 'B'],
    related_agent_records: [],
    related_tests: [],
    impact_facts: [],
    agent_claims: [],
    mismatches: [],
    provenance_refs: [],
    hunk_review_items: Array.from({ length: 5 }, (_, index) => ({
      hunk_id: `hunk_00${index + 1}`,
      file_id: 'cf_1',
      path: 'backend/app/schemas/assessment.py',
      priority: 100,
      risk_level: 'high',
      reasons: duplicateReasons,
      fact_basis: ['public_surface_path', 'claim_fact_mismatch', 'test_evidence:unknown', 'large_diff'],
      provenance_refs: [],
      mismatch_ids: ['mm_1'],
    })),
    file_assessment: {
      why_changed: 'No structured agent reason is available.',
      impact_summary: 'Review the diff.',
      test_summary: 'No direct test evidence was found.',
      recommended_action: 'Review this file manually.',
      generated_by: 'rules',
      agent_status: 'not_run',
      agent_source: null,
      confidence: 'low',
      evidence_refs: ['git_diff'],
      unknowns: [],
    },
    review_state: {
      review_status: 'unreviewed',
      diff_fingerprint: 'sha256:file',
      reviewer: null,
      reviewed_at: null,
      notes: [],
    },
  }
}

function detailWithStructuredProvenance(): ChangedFileDetail {
  return {
    ...detailWithDuplicateHunkChecks(),
    file: {
      ...detailWithDuplicateHunkChecks().file,
      path: 'frontend/src/api/client.ts',
    },
    provenance_refs: [
      {
        source: 'tool:apply_patch',
        session_id: 'sess_1',
        message_ref: '',
        tool_call_ref: 'call_patch_1',
        command: '',
        file_path: 'frontend/src/api/client.ts',
        hunk_id: 'hunk_001',
        confidence: 'high',
      },
      {
        source: 'codex_command',
        session_id: 'sess_1',
        message_ref: '',
        tool_call_ref: 'call_exec_1',
        command: "npm test -- api",
        file_path: 'frontend/src/api/client.ts',
        hunk_id: 'hunk_001',
        confidence: 'medium',
      },
      {
        source: 'message:user',
        session_id: 'sess_1',
        message_ref: 'msg_user_1',
        tool_call_ref: '',
        command: '',
        file_path: 'frontend/src/api/client.ts',
        hunk_id: '',
        confidence: 'medium',
      },
    ],
  }
}

function detailWithDiffOnlyProvenance(): ChangedFileDetail {
  return {
    ...detailWithDuplicateHunkChecks(),
    provenance_refs: [
      {
        source: 'git_diff',
        session_id: 'sess_1',
        message_ref: '',
        tool_call_ref: '',
        command: '',
        file_path: 'backend/app/schemas/assessment.py',
        hunk_id: 'hunk_001',
        confidence: 'medium',
      },
    ],
  }
}

describe('FileEvidencePanel', () => {
  afterEach(() => cleanup())

  it('deduplicates repeated hunk priority reasons in fact checks', () => {
    render(<FileEvidencePanel detail={detailWithDuplicateHunkChecks()} />)

    const factChecks = screen.getByRole('heading', { name: 'Fact Checks' }).closest('section')

    expect(factChecks).not.toBeNull()
    expect(within(factChecks as HTMLElement).getAllByText('Priority 100')).toHaveLength(1)
    expect(
      within(factChecks as HTMLElement).getByText(/Public API\/type\/config surface changed.*5 hunks/),
    ).toBeInTheDocument()
  })

  it('renders provenance as readable evidence chain', () => {
    render(<FileEvidencePanel detail={detailWithStructuredProvenance()} />)

    const provenance = screen.getByRole('heading', { name: 'Provenance' }).closest('section')

    expect(provenance).not.toBeNull()
    expect(within(provenance as HTMLElement).getByText('High · apply_patch changed this file')).toBeInTheDocument()
    expect(within(provenance as HTMLElement).getByText(/tool call call_patch_1 · hunk_001/)).toBeInTheDocument()
    expect(within(provenance as HTMLElement).getByText('Medium · command touched this file')).toBeInTheDocument()
    expect(within(provenance as HTMLElement).getByText(/npm test -- api/)).toBeInTheDocument()
    expect(within(provenance as HTMLElement).getByText('Medium · message mentioned this file')).toBeInTheDocument()
    expect(within(provenance as HTMLElement).getByText(/message msg_user_1/)).toBeInTheDocument()
  })

  it('does not present git diff as agent provenance', () => {
    render(<FileEvidencePanel detail={detailWithDiffOnlyProvenance()} />)

    const provenance = screen.getByRole('heading', { name: 'Provenance' }).closest('section')

    expect(provenance).not.toBeNull()
    expect(within(provenance as HTMLElement).getByText('No agent-specific provenance was linked to this file.')).toBeInTheDocument()
    expect(within(provenance as HTMLElement).getByText(/Only git diff evidence is available/)).toBeInTheDocument()
    expect(within(provenance as HTMLElement).queryByText(/git diff contains this file/)).not.toBeInTheDocument()
  })
})
