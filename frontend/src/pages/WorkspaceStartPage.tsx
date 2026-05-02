import { useEffect, useMemo, useState } from 'react'
import { triggerAssessmentRebuild } from '../api/assessments'
import { fetchJob } from '../api/jobs'
import { readStoredLanguage, storeLanguage, type Language } from '../i18n'
import type { JobState } from '../types/api'
import styles from './WorkspaceStartPage.module.css'

function inferRepoKey(path: string) {
  const name = path.trim().replace(/\/+$/, '').split('/').pop() ?? ''
  return name.replace(/[^a-zA-Z0-9_-]+/g, '_') || 'local_repo'
}

function targetPath() {
  if (window.location.pathname.startsWith('/precommit')) return '/precommit'
  return window.location.pathname.startsWith('/tests') ? '/tests' : '/'
}

function copy(language: Language) {
  if (language === 'zh-CN') {
    return {
      title: '选择要检查的工程',
      subtitle: '输入本地 Git 仓库路径后启动分析。完成后会进入变更审查页，保留 Agent 分析、测试管理和中英切换流程。',
      workspaceLabel: '工程路径',
      workspaceHint: '例如 /Users/tc/ai/whether_commit',
      repoLabel: '仓库标识',
      repoHint: '用于本地快照存储，默认从路径名生成。',
      start: '开始分析',
      open: '打开已存在分析',
      running: '分析运行中',
      queued: '分析已排队',
      failed: '分析失败',
      required: '请先输入工程路径。',
      zh: '简体中文',
      en: 'English',
    }
  }
  return {
    title: 'Select a Workspace',
    subtitle: 'Enter a local Git repository path to start analysis. The review page keeps agent assessment, test management, and language switching intact.',
    workspaceLabel: 'Workspace path',
    workspaceHint: 'Example: /Users/tc/ai/whether_commit',
    repoLabel: 'Repository key',
    repoHint: 'Used for local snapshot storage. Generated from the path by default.',
    start: 'Start analysis',
    open: 'Open existing analysis',
    running: 'Analysis running',
    queued: 'Analysis queued',
    failed: 'Analysis failed',
    required: 'Enter a workspace path first.',
    zh: '简体中文',
    en: 'English',
  }
}

export function WorkspaceStartPage() {
  const [language, setLanguage] = useState<Language>(() => readStoredLanguage())
  const [workspacePath, setWorkspacePath] = useState('')
  const [repoKey, setRepoKey] = useState('')
  const [manualRepoKey, setManualRepoKey] = useState(false)
  const [job, setJob] = useState<JobState | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const text = copy(language)

  const resolvedRepoKey = useMemo(
    () => (repoKey.trim() || inferRepoKey(workspacePath)),
    [repoKey, workspacePath],
  )

  useEffect(() => {
    if (manualRepoKey) return
    setRepoKey(inferRepoKey(workspacePath))
  }, [manualRepoKey, workspacePath])

  useEffect(() => {
    if (!job || !['pending', 'running'].includes(job.status)) return
    const timer = window.setInterval(() => {
      fetchJob(job.job_id)
        .then(nextJob => {
          setJob(nextJob)
          if (nextJob.status === 'success' || nextJob.status === 'partial_success') {
            const params = new URLSearchParams({
              repo_key: resolvedRepoKey,
              workspace_path: workspacePath.trim(),
            })
            window.location.href = `${targetPath()}?${params.toString()}`
          }
          if (nextJob.status === 'failed') {
            setError(nextJob.message || text.failed)
            setIsStarting(false)
          }
        })
        .catch(err => {
          setError(String(err))
          setIsStarting(false)
        })
    }, 1000)
    return () => window.clearInterval(timer)
  }, [job, resolvedRepoKey, text.failed, workspacePath])

  const changeLanguage = (nextLanguage: Language) => {
    setLanguage(nextLanguage)
    storeLanguage(nextLanguage)
  }

  const openAssessment = () => {
    if (!workspacePath.trim()) {
      setError(text.required)
      return
    }
    const params = new URLSearchParams({
      repo_key: resolvedRepoKey,
      workspace_path: workspacePath.trim(),
    })
    window.location.href = `${targetPath()}?${params.toString()}`
  }

  const startAssessment = async () => {
    if (!workspacePath.trim() || isStarting) {
      setError(text.required)
      return
    }
    setError(null)
    setIsStarting(true)
    try {
      const response = await triggerAssessmentRebuild({
        repo_key: resolvedRepoKey,
        workspace_path: workspacePath.trim(),
        base_commit_sha: 'AUTO_MERGE_BASE',
      })
      setJob({
        job_id: response.job_id,
        repo_key: resolvedRepoKey,
        status: 'pending',
        step: 'init',
        progress: 0,
        message: text.queued,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
    } catch (err) {
      setError(String(err))
      setIsStarting(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.topbar}>
        <button
          className={`${styles.languageButton} ${language === 'zh-CN' ? styles.languageButtonActive : ''}`}
          onClick={() => changeLanguage('zh-CN')}
        >
          {text.zh}
        </button>
        <button
          className={`${styles.languageButton} ${language === 'en-US' ? styles.languageButtonActive : ''}`}
          onClick={() => changeLanguage('en-US')}
        >
          {text.en}
        </button>
      </div>
      <main className={styles.shell}>
        <h1 className={styles.title}>{text.title}</h1>
        <p className={styles.subtitle}>{text.subtitle}</p>
        <div className={styles.form}>
          <label className={styles.field}>
            <span className={styles.label}>{text.workspaceLabel}</span>
            <input
              className={styles.input}
              value={workspacePath}
              onChange={event => setWorkspacePath(event.target.value)}
              placeholder={text.workspaceHint}
            />
          </label>
          <label className={styles.field}>
            <span className={styles.label}>{text.repoLabel}</span>
            <input
              className={styles.input}
              value={repoKey}
              onChange={event => {
                setManualRepoKey(true)
                setRepoKey(event.target.value)
              }}
            />
            <span className={styles.hint}>{text.repoHint}</span>
          </label>
          {error ? <div className={styles.error}>{error}</div> : null}
          <div className={styles.actions}>
            <button className={styles.primary} onClick={startAssessment} disabled={isStarting}>
              {isStarting ? text.running : text.start}
            </button>
            <button className={styles.secondary} onClick={openAssessment} disabled={isStarting}>
              {text.open}
            </button>
            <span className={styles.status}>{job ? `${job.step} · ${job.progress}% · ${job.message}` : null}</span>
          </div>
        </div>
      </main>
    </div>
  )
}
