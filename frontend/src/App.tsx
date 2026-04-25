import { AssessmentReviewPage } from './pages/AssessmentReviewPage'
import { TestChangesPage } from './pages/TestChangesPage'

export default function App() {
  return window.location.pathname.startsWith('/tests')
    ? <TestChangesPage />
    : <AssessmentReviewPage />
}
