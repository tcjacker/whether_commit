import type { AssessmentManifest, ChangedFileDetail, HunkReviewItem } from '../types/api'

function firstHunkId(detail: ChangedFileDetail) {
  return detail.diff_hunks[0]?.hunk_id ?? 'hunk_preview'
}

function isContractPath(path: string) {
  return /api|schema|types|contract|route|endpoint/i.test(path)
}

function isConfigPath(path: string) {
  return /config|vite|eslint|tsconfig|package\.json/i.test(path)
}

function previewPriorityForFile(
  file: ChangedFileDetail['file'],
  relatedTests: ChangedFileDetail['related_tests'] = [],
) {
  const path = file.path
  let score = 20
  const reasons: string[] = []
  const factBasis: string[] = []

  if (isContractPath(path)) {
    score += 35
    reasons.push('Preview: public contract or type surface changed')
    factBasis.push('preview_contract_surface')
  }
  if (file.coverage_status === 'missing' || relatedTests.length === 0) {
    score += 25
    reasons.push('Preview: no direct executed test evidence')
    factBasis.push('preview_no_execution_record')
  }
  if (file.additions + file.deletions >= 25) {
    score += 12
    reasons.push('Preview: large hunk or file-level change')
    factBasis.push('preview_large_change')
  }
  if (isConfigPath(path)) {
    score += 8
    reasons.push('Preview: config/build surface changed')
    factBasis.push('preview_config_surface')
  }

  return {
    priority: Math.min(score, 92),
    riskLevel: score >= 70 ? 'high' as const : score >= 40 ? 'medium' as const : 'low' as const,
    reasons: reasons.length ? reasons : ['Preview: low-priority local change'],
    factBasis: factBasis.length ? factBasis : ['preview_diff_fact'],
  }
}

function previewHunkItem(detail: ChangedFileDetail): HunkReviewItem {
  const hunkId = firstHunkId(detail)
  const score = previewPriorityForFile(detail.file, detail.related_tests)
  return {
    hunk_id: hunkId,
    file_id: detail.file.file_id,
    path: detail.file.path,
    priority: score.priority,
    risk_level: score.riskLevel,
    reasons: score.reasons,
    fact_basis: score.factBasis,
    provenance_refs: [],
    mismatch_ids: ['preview_mismatch_001'],
  }
}

export function withV02PreviewManifest(manifest: AssessmentManifest): AssessmentManifest {
  const previewFileList = manifest.file_list.map(file => {
    const score = previewPriorityForFile(file)
    return {
      ...file,
      risk_level: score.riskLevel,
      highest_hunk_priority: score.priority,
      mismatch_count: score.priority >= 70 ? 1 : 0,
      weakest_test_evidence_grade: 'claimed' as const,
    }
  })

  return {
    ...manifest,
    mode: manifest.mode ?? 'working_tree',
    provenance_capture_level: manifest.provenance_capture_level ?? manifest.agentic_summary.capture_level,
    mismatch_count: manifest.mismatch_count ?? 1,
    weak_test_evidence_count: manifest.weak_test_evidence_count ?? 1,
    review_decision: manifest.review_decision ?? 'needs_tests',
    hunk_queue_preview: manifest.hunk_queue_preview ?? [],
    summary: {
      ...manifest.summary,
      overall_risk_level: manifest.summary.overall_risk_level === 'unknown' ? 'medium' : manifest.summary.overall_risk_level,
      coverage_status: manifest.summary.coverage_status === 'unknown' ? 'missing' : manifest.summary.coverage_status,
    },
    file_list: previewFileList,
  }
}

export function withV02PreviewDetail(detail: ChangedFileDetail): ChangedFileDetail {
  const hunkItem = previewHunkItem(detail)
  return {
    ...detail,
    file: {
      ...detail.file,
      risk_level: hunkItem.risk_level,
      highest_hunk_priority: hunkItem.priority,
      mismatch_count: hunkItem.priority >= 70 ? 1 : 0,
      weakest_test_evidence_grade: 'claimed',
    },
    agent_claims: detail.agent_claims?.length ? detail.agent_claims : [{
      claim_id: 'preview_claim_001',
      type: 'test',
      text: '[Preview] Agent claimed this change has test coverage, but the fact layer has not verified an executed test.',
      source: 'codex',
      session_id: 'preview_session',
      message_ref: 'assistant_msg_preview',
      tool_call_ref: 'apply_patch',
      related_files: [detail.file.path],
      confidence: 'medium',
    }],
    mismatches: detail.mismatches?.length ? detail.mismatches : [{
      mismatch_id: 'preview_mismatch_001',
      kind: 'claimed_tested_but_no_executed_test_evidence',
      claim_id: 'preview_claim_001',
      severity: 'high',
      explanation: '[Preview] Agent claim says tests cover the change, but no executed test evidence is present in this assessment.',
      fact_refs: ['preview_no_execution_record'],
      provenance_refs: [],
    }],
    provenance_refs: detail.provenance_refs?.length ? detail.provenance_refs : [{
      source: 'codex',
      session_id: 'preview_session',
      message_ref: 'assistant_msg_preview',
      tool_call_ref: 'apply_patch',
      command: '',
      file_path: detail.file.path,
      hunk_id: hunkItem.hunk_id,
      confidence: 'medium',
    }],
    hunk_review_items: detail.hunk_review_items?.length ? detail.hunk_review_items : [hunkItem],
  }
}
