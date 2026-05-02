import { useState } from 'react'
import type { DiffLine, TestCaseDetail } from '../../types/api'
import styles from './TestCaseCodePanel.module.css'

type CodeTab = 'diff' | 'body' | 'assertions'

const tabs: Array<{ id: CodeTab; label: string }> = [
  { id: 'diff', label: 'Diff' },
  { id: 'body', label: 'Full test body' },
  { id: 'assertions', label: 'Assertions only' },
]

function linePrefix(type: DiffLine['type']) {
  if (type === 'add') return '+'
  if (type === 'remove') return '-'
  return ' '
}

function lineClass(type: DiffLine['type']) {
  if (type === 'add') return styles.add
  if (type === 'remove') return styles.remove
  if (type === 'header') return styles.headerLine
  return styles.context
}

function renderLines(lines: DiffLine[], keyPrefix: string) {
  if (lines.length === 0) return <p className={styles.empty}>No code lines available.</p>

  return lines.map((line, index) => (
    <pre key={`${keyPrefix}-${index}`} className={lineClass(line.type)}>
      {linePrefix(line.type)}
      {line.content}
    </pre>
  ))
}

export function TestCaseCodePanel({ detail }: { detail: TestCaseDetail | null }) {
  const [activeTab, setActiveTab] = useState<CodeTab>('diff')

  if (!detail) {
    return (
      <main className={styles.panel} aria-label="test-code">
        <p className={styles.selectMessage}>Select a test case to inspect its code.</p>
      </main>
    )
  }

  return (
    <main className={styles.panel} aria-label="test-code">
      <header className={styles.header}>
        <div>
          <h2>{detail.test_case.name}</h2>
          <span>{detail.test_case.path}</span>
        </div>
        <div className={styles.tabs} aria-label="test-code-sections">
          {tabs.map(tab => (
            <button
              key={tab.id}
              type="button"
              className={activeTab === tab.id ? styles.activeTab : styles.tab}
              onClick={() => setActiveTab(tab.id)}
              aria-pressed={activeTab === tab.id}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>
      <div className={styles.code}>
        {activeTab === 'diff'
          ? detail.diff_hunks.map(hunk => (
            <section key={hunk.hunk_id} className={styles.hunk}>
              <div className={styles.hunkHeader}>
                <span>{hunk.hunk_id}</span>
                <strong>
                  -{hunk.old_start},{hunk.old_lines} +{hunk.new_start},{hunk.new_lines}
                </strong>
              </div>
              {renderLines(hunk.lines, hunk.hunk_id)}
            </section>
          ))
          : renderLines(activeTab === 'body' ? detail.full_body : detail.assertions, activeTab)}
      </div>
    </main>
  )
}
