import styles from './EmptyState.module.css'

interface Props {
  message: string
  action?: { label: string; onClick: () => void }
}

export function EmptyState({ message, action }: Props) {
  return (
    <div className={styles.wrap}>
      <p className={styles.msg}>{message}</p>
      {action && (
        <button className={styles.btn} onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  )
}
