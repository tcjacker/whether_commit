import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { PageHeader } from '../PageHeader'

afterEach(() => {
  cleanup()
})

describe('PageHeader', () => {
  it('renders an explicit change review entry for the current repo', () => {
    const onWorkspacePathChange = vi.fn()

    render(
      <PageHeader
        repo={null}
        repoKey="divide_prd_to_ui"
        workspacePath="/path/to/repo"
        snapshot={null}
        loadingState="idle"
        jobProgress={null}
        onRebuild={() => {}}
        onWorkspacePathChange={onWorkspacePathChange}
        onClearSelection={() => {}}
        hasSelection={false}
      />,
    )

    const link = screen.getByRole('link', { name: '进入 Change Review' })
    expect(link).toHaveAttribute(
      'href',
      '/review-graph?repo_key=divide_prd_to_ui&workspace_path=%2FUsers%2Ftc%2Fdivide_prd_to_ui',
    )

    const input = screen.getByLabelText('Workspace Path')
    expect(input).toHaveValue('/path/to/repo')

    fireEvent.change(input, { target: { value: '/tmp/alt-repo' } })
    expect(onWorkspacePathChange).toHaveBeenCalledWith('/tmp/alt-repo')
  })
})
