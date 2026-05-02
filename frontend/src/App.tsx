import { AssessmentReviewPage } from './pages/AssessmentReviewPage'
import { TestChangesPage } from './pages/TestChangesPage'
import { WorkspaceStartPage } from './pages/WorkspaceStartPage'

export default function App() {
  const params = new URLSearchParams(window.location.search)
  if (!params.get('workspace_path')) return <WorkspaceStartPage />
  return window.location.pathname.startsWith('/tests')
    ? <TestChangesPage />
    : <AssessmentReviewPage />
}
