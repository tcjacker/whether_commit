import type { ReactNode } from 'react'
import styles from './DashboardGrid.module.css'

interface Props {
  children: ReactNode
}

export function DashboardGrid({ children }: Props) {
  return <div className={styles.grid}>{children}</div>
}
