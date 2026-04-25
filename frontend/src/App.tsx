import { AssessmentReviewPage } from './pages/AssessmentReviewPage'
import { OverviewPage } from './pages/OverviewPage'
import { ReviewGraphPage } from './pages/ReviewGraphPage'

export default function App() {
  return window.location.pathname.startsWith('/review-graph')
    ? <ReviewGraphPage />
    : window.location.pathname.startsWith('/legacy-overview')
      ? <OverviewPage />
      : <AssessmentReviewPage />
}
