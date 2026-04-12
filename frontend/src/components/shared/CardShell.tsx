import type { ReactNode } from 'react'
import styles from './CardShell.module.css'

interface Props {
  title: string
  subtitle?: string
  badge?: ReactNode
  children: ReactNode
  className?: string
  dimmed?: boolean
}

export function CardShell({ title, subtitle, badge, children, className = '', dimmed }: Props) {
  return (
    <div className={`${styles.card} ${dimmed ? styles.dimmed : ''} ${className}`}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>{title}</h3>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
        {badge && <div className={styles.badge}>{badge}</div>}
      </div>
      <div className={styles.body}>{children}</div>
    </div>
  )
}
