import { describe, expect, it } from 'vitest'
import { withV02PreviewDetail, withV02PreviewManifest } from '../assessmentPreview'
import type { AssessmentManifest, ChangedFileDetail } from '../../types/api'

const manifest: AssessmentManifest = {
  assessment_id: 'aca_ws_1',
  workspace_snapshot_id: 'ws_1',
  repo_key: 'demo',
  status: 'ready',
  agentic_summary: {
    generated_by: 'codex_logs',
    capture_level: 'partial',
    confidence: 'medium',
    time_window: { since_commit: 'HEAD', since_commit_time: null },
    user_design_goal: '',
    codex_change_summary: '',
    main_objective: '',
    key_decisions: [],
    files_or_areas_changed: [],
    tests_and_verification: [],
    unknowns: [],
  },
  summary: {
    headline: '本次变更包含 1 个待审查文件。',
    overall_risk_level: 'medium',
    coverage_status: 'missing',
    changed_file_count: 1,
    unreviewed_file_count: 1,
    affected_capability_count: 0,
    missing_test_count: 1,
    agent_sources: ['codex', 'git_diff'],
    recommended_review_order: ['frontend/src/types/api.ts'],
  },
  file_list: [{
    file_id: 'cf_1',
    path: 'frontend/src/types/api.ts',
    old_path: null,
    status: 'modified',
    additions: 70,
    deletions: 4,
    risk_level: 'medium',
    coverage_status: 'missing',
    review_status: 'unreviewed',
    agent_sources: ['codex', 'git_diff'],
    diff_fingerprint: 'sha256:abc',
  }],
  risk_signals_summary: [],
  agent_sources: ['codex', 'git_diff'],
  review_progress: { total: 1, reviewed: 0, needs_follow_up: 0, needs_recheck: 0, unreviewed: 1 },
}

const detail: ChangedFileDetail = {
  file: manifest.file_list[0],
  diff_hunks: [{
    hunk_id: 'hunk_001',
    old_start: 1,
    old_lines: 1,
    new_start: 1,
    new_lines: 2,
    hunk_fingerprint: 'sha256:def',
    lines: [{ type: 'add', content: 'export type EvidenceGrade = ...' }],
  }],
  changed_symbols: [],
  related_agent_records: [],
  related_tests: [],
  impact_facts: [],
  file_assessment: {
    why_changed: 'Rule fallback.',
    impact_summary: 'Review the diff.',
    test_summary: 'No direct test evidence was found.',
    recommended_action: 'Review manually.',
    generated_by: 'rules',
    agent_status: 'not_run',
    agent_source: null,
    confidence: 'low',
    evidence_refs: ['git_diff'],
    unknowns: [],
  },
  review_state: {
    review_status: 'unreviewed',
    diff_fingerprint: 'sha256:abc',
    reviewer: null,
    reviewed_at: null,
    notes: [],
  },
}

describe('assessment v0.2 preview decorators', () => {
  it('adds visible v0.2 preview signals to old-schema assessment data', () => {
    const previewManifest = withV02PreviewManifest(manifest)
    const previewDetail = withV02PreviewDetail(detail)

    expect(previewManifest.mode).toBe('working_tree')
    expect(previewManifest.review_decision).toBe('needs_tests')
    expect(previewManifest.mismatch_count).toBe(1)
    expect(previewManifest.file_list[0].highest_hunk_priority).toBe(92)
    expect(previewDetail.agent_claims?.[0].text).toContain('[Preview]')
    expect(previewDetail.mismatches?.[0].kind).toBe('claimed_tested_but_no_executed_test_evidence')
    expect(previewDetail.provenance_refs?.[0].session_id).toBe('preview_session')
    expect(previewDetail.hunk_review_items?.[0].priority).toBe(92)
  })

  it('varies preview hunk priority by file characteristics', () => {
    const configDetail: ChangedFileDetail = {
      ...detail,
      file: {
        ...detail.file,
        file_id: 'cf_config',
        path: 'frontend/vite.config.ts',
        additions: 10,
        deletions: 3,
      },
      diff_hunks: [{
        ...detail.diff_hunks[0],
        hunk_id: 'hunk_config',
        lines: [{ type: 'add', content: 'server: { port: 4174 }' }],
      }],
    }

    const sourcePriority = withV02PreviewDetail(detail).hunk_review_items?.[0].priority
    const configPriority = withV02PreviewDetail(configDetail).hunk_review_items?.[0].priority

    expect(sourcePriority).toBeGreaterThan(configPriority ?? 0)
    expect(configPriority).not.toBe(sourcePriority)
  })
})
