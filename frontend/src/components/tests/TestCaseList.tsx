import type { TestCaseSummary, TestManagementSummary } from '../../types/api'
import { t, zhStatus, type Language } from '../../i18n'
import styles from './TestCaseList.module.css'

function formatValue(value: string, language: Language) {
  return zhStatus(value, language)
}

export function TestCaseList({
  summary,
  selectedTestCaseId,
  onSelect,
  language = 'en-US',
}: {
  summary: TestManagementSummary
  selectedTestCaseId: string | null
  onSelect: (testCase: TestCaseSummary) => void
  language?: Language
}) {
  return (
    <aside className={styles.panel} aria-label="test-cases">
      <header className={styles.header}>
        <h2>{t(language, 'testCases')}</h2>
        <span>{summary.test_case_count}</span>
      </header>
      <div className={styles.groups}>
        {summary.files.map(file => (
          <section key={file.file_id} className={styles.group}>
            <div className={styles.fileHeader}>
              <span className={styles.path}>{file.path}</span>
              <span className={styles.fileMeta}>
                {formatValue(file.status, language)} · {file.test_case_count}
              </span>
            </div>
            <ul className={styles.list}>
              {file.test_cases.map(testCase => (
                <li key={testCase.test_case_id}>
                  <button
                    className={testCase.test_case_id === selectedTestCaseId ? styles.selected : styles.caseButton}
                    onClick={() => onSelect(testCase)}
                  >
                    <span className={styles.caseName}>{testCase.name}</span>
                    <span className={styles.caseMeta}>{formatValue(testCase.status, language)}</span>
                    <span className={styles.badges}>
                      <span>{formatValue(testCase.evidence_grade, language)}</span>
                      <span>{formatValue(testCase.extraction_confidence, language)}</span>
                      <span>{formatValue(testCase.last_status, language)}</span>
                      {testCase.highest_risk_covered_hunk_id ? (
                        <span>{testCase.highest_risk_covered_hunk_id}</span>
                      ) : null}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </aside>
  )
}
