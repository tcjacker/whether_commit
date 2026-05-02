import { AssessmentReviewPage } from './pages/AssessmentReviewPage'
import { PrecommitReviewPage } from './pages/PrecommitReviewPage'
import { TestChangesPage } from './pages/TestChangesPage'
import { WorkspaceStartPage } from './pages/WorkspaceStartPage'

export default function App() {
  const params = new URLSearchParams(window.location.search)
  if (!params.get('workspace_path')) return <WorkspaceStartPage />
  if (window.location.pathname.startsWith('/precommit')) return <PrecommitReviewPage />
  return window.location.pathname.startsWith('/tests')
    ? <TestChangesPage />
    : <AssessmentReviewPage />
}
