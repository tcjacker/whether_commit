import { AssessmentReviewPage } from './pages/AssessmentReviewPage'
import { OverviewPage } from './pages/OverviewPage'
import { ReviewGraphPage } from './pages/ReviewGraphPage'
import { TestChangesPage } from './pages/TestChangesPage'

export default function App() {
  return window.location.pathname.startsWith('/review-graph')
    ? <ReviewGraphPage />
    : window.location.pathname.startsWith('/tests')
      ? <TestChangesPage />
    : window.location.pathname.startsWith('/legacy-overview')
      ? <OverviewPage />
      : <AssessmentReviewPage />
}
