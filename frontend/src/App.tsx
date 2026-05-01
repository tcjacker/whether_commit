import { AssessmentReviewPage } from './pages/AssessmentReviewPage'
import { PrecommitReviewPage } from './pages/PrecommitReviewPage'
import { TestChangesPage } from './pages/TestChangesPage'

export default function App() {
  if (window.location.pathname.startsWith('/precommit')) return <PrecommitReviewPage />
  return window.location.pathname.startsWith('/tests')
    ? <TestChangesPage />
    : <AssessmentReviewPage />
}
