import { t, type Language } from '../../i18n'
import styles from './RebuildButton.module.css'

interface Props {
  isRebuilding: boolean
  onClick: () => void
  language?: Language
}

export function RebuildButton({ isRebuilding, onClick, language = 'zh-CN' }: Props) {
  return (
    <button className={styles.btn} disabled={isRebuilding} onClick={onClick}>
      {isRebuilding ? (
        <>
          <span className={styles.spinner} />
          {t(language, 'rebuilding')}
        </>
      ) : (
        <>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
            <path d="M1.5 8a6.5 6.5 0 1 1 13 0A6.5 6.5 0 0 1 1.5 8zM8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zm.75 4.75a.75.75 0 0 0-1.5 0v3.5l-1.75 1.75a.75.75 0 0 0 1.06 1.06l2-2A.75.75 0 0 0 8.75 8.5V4.75z"/>
          </svg>
          {t(language, 'rebuild')}
        </>
      )}
    </button>
  )
}
