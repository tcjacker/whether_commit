import { afterEach, describe, expect, it, vi } from 'vitest'
import { triggerFileAgentAssessment } from '../assessments'

describe('assessment api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts codex assessment requests in Chinese by default', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await triggerFileAgentAssessment('demo', 'aca_ws_1', 'cf_abc123', '/tmp/demo')

    const url = String(fetchSpy.mock.calls[0][0])
    expect(url).toContain('/api/assessments/aca_ws_1/files/cf_abc123/agent-assessment?')
    expect(url).toContain('repo_key=demo')
    expect(url).toContain('workspace_path=%2Ftmp%2Fdemo')
    expect(url).toContain('language=zh-CN')
  })
})
