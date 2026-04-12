import { useMemo, useRef, useEffect, useState } from 'react'
import type { ArchitectureNode, ArchitectureEdge } from '../../types/api'

interface Props {
  nodes: ArchitectureNode[]
  edges: ArchitectureEdge[]
  highlightedNodeIds: Set<string>
  height?: number
}

// Node fill colors by type
const TYPE_COLOR: Record<string, string> = {
  'router':               '#1d4ed8',
  'api handler':          '#0d9488',
  'service':              '#7c3aed',
  'repository':           '#059669',
  'db model':             '#065f46',
  'worker':               '#b45309',
  'external integration': '#64748b',
  'config':               '#475569',
  'gateway':              '#9d174d',
  'database':             '#065f46',
  'external':             '#475569',
  'cache':                '#b45309',
  'queue':                '#92400e',
}

function typeColor(t: string): string {
  return TYPE_COLOR[t.toLowerCase()] ?? '#4b5563'
}

interface NodePos {
  id: string
  x: number
  y: number
  label: string
  type: string
  health?: string
}

function layoutNodes(nodes: ArchitectureNode[], W: number, H: number): NodePos[] {
  if (!nodes.length) return []
  const n = nodes.length
  const cx = W / 2
  const cy = H / 2
  const r = Math.min(cx, cy) - 60

  return nodes.map((node, i) => {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2
    return {
      id: node.id,
      x: n <= 1 ? cx : cx + r * Math.cos(angle),
      y: n <= 1 ? cy : cy + r * Math.sin(angle),
      label: node.name,
      type: node.type,
      health: node.health,
    }
  })
}

const NW = 110 // node width
const NH = 36  // node height

export function ArchitectureDiagram({ nodes, edges, highlightedNodeIds, height = 340 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(800)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      const w = entries[0]?.contentRect.width
      if (w) setWidth(w)
    })
    ro.observe(el)
    setWidth(el.clientWidth || 800)
    return () => ro.disconnect()
  }, [])

  const positions = useMemo(() => layoutNodes(nodes, width, height), [nodes, width, height])
  const posMap = useMemo(() => {
    const m: Record<string, NodePos> = {}
    positions.forEach(p => (m[p.id] = p))
    return m
  }, [positions])

  const hasHighlight = highlightedNodeIds.size > 0

  return (
    <div ref={containerRef} style={{ width: '100%' }}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ display: 'block' }}
      >
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#4b5563" />
          </marker>
          <marker id="arrow-hl" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#a78bfa" />
          </marker>
        </defs>

        {/* Edges */}
        {edges.map((e, i) => {
          const from = posMap[e.source]
          const to = posMap[e.target]
          if (!from || !to) return null
          const isHl = hasHighlight && (highlightedNodeIds.has(e.source) || highlightedNodeIds.has(e.target))
          const opacity = hasHighlight ? (isHl ? 1 : 0.1) : 0.4
          return (
            <line
              key={i}
              x1={from.x} y1={from.y}
              x2={to.x} y2={to.y}
              stroke={isHl ? '#6366f1' : '#4b5563'}
              strokeWidth={isHl ? 1.5 : 1}
              opacity={opacity}
              markerEnd={isHl ? 'url(#arrow-hl)' : 'url(#arrow)'}
            />
          )
        })}

        {/* Nodes */}
        {positions.map(p => {
          const isHl = highlightedNodeIds.has(p.id)
          const dimmed = hasHighlight && !isHl
          const fill = typeColor(p.type)
          const displayLabel = p.label.length > 14 ? p.label.slice(0, 13) + '…' : p.label

          return (
            <g
              key={p.id}
              transform={`translate(${p.x - NW / 2}, ${p.y - NH / 2})`}
              opacity={dimmed ? 0.2 : 1}
            >
              <rect
                width={NW}
                height={NH}
                rx={6}
                fill={fill}
                fillOpacity={0.2}
                stroke={isHl ? '#a78bfa' : fill}
                strokeWidth={isHl ? 2 : 1}
              />
              {/* Health dot */}
              {p.health === 'warning' && (
                <circle cx={NW - 8} cy={8} r={4} fill="#d29922" />
              )}
              {p.health === 'ok' && (
                <circle cx={NW - 8} cy={8} r={4} fill="#3fb950" />
              )}
              <text
                x={NW / 2}
                y={NH / 2 + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={isHl ? '#e2e8f0' : '#9ca3af'}
                fontSize={11}
                fontFamily="system-ui, sans-serif"
                fontWeight={isHl ? '600' : '400'}
              >
                {displayLabel}
              </text>
              {/* Type label */}
              <text
                x={NW / 2}
                y={NH + 12}
                textAnchor="middle"
                fill="#6b7280"
                fontSize={9}
                fontFamily="system-ui, sans-serif"
              >
                {p.type}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
