interface Props {
  height?: number | string
  width?: number | string
  lines?: number
  gap?: number
}

export function SkeletonBlock({ height = 16, width = '100%', lines = 1, gap = 8 }: Props) {
  if (lines > 1) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap }}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="skeleton"
            style={{ height, width: i === lines - 1 ? '65%' : width }}
          />
        ))}
      </div>
    )
  }
  return <div className="skeleton" style={{ height, width }} />
}
