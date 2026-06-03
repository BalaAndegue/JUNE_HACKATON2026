'use client'

import { memo, type ReactNode } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { cn } from '@/lib/utils'
import { useEditorStore } from '@/store/editor.store'
import type { NodeStatus } from '@/types'
import { CheckCircle2, XCircle, Loader2, Pin } from 'lucide-react'

interface BaseNodeProps extends NodeProps {
  color?: string
  icon?: ReactNode
  label?: string
  showInputHandle?: boolean
  showOutputHandle?: boolean
  children?: ReactNode
}

const statusConfig: Record<NodeStatus, { border: string; glow: string; icon: ReactNode }> = {
  idle: { border: 'border-[#2a2a2a]', glow: '', icon: null },
  running: {
    border: 'border-blue-500',
    glow: 'shadow-[0_0_12px_rgba(59,130,246,0.35)]',
    icon: <Loader2 className="h-3 w-3 text-blue-400 animate-spin" />,
  },
  success: {
    border: 'border-emerald-500',
    glow: 'shadow-[0_0_10px_rgba(16,185,129,0.25)]',
    icon: <CheckCircle2 className="h-3 w-3 text-emerald-400" />,
  },
  error: {
    border: 'border-red-500',
    glow: 'shadow-[0_0_10px_rgba(239,68,68,0.25)]',
    icon: <XCircle className="h-3 w-3 text-red-400" />,
  },
  skipped: { border: 'border-gray-700', glow: '', icon: null },
}

export const BaseNode = memo(({
  id, data, selected, color = '#6b7280',
  icon, label, showInputHandle = true, showOutputHandle = true,
  children,
}: BaseNodeProps) => {
  const nodeStatuses = useEditorStore((s) => s.nodeStatuses)
  const setSelectedNode = useEditorStore((s) => s.setSelectedNode)
  const d = data as Record<string, unknown>
  const status: NodeStatus = nodeStatuses[id] ?? (d.status as NodeStatus) ?? 'idle'
  const { border, glow, icon: statusIcon } = statusConfig[status]

  return (
    <div
      className={cn(
        'relative min-w-[180px] max-w-[240px] rounded-xl border-2 bg-[#141414] transition-all duration-150 cursor-pointer select-none',
        border,
        glow,
        selected && 'ring-2 ring-[#ff6d35] ring-offset-1 ring-offset-[#0a0a0a]'
      )}
      onClick={() => setSelectedNode(id)}
    >
      {/* Input handle */}
      {showInputHandle && (
        <Handle
          type="target"
          position={Position.Left}
          className="!h-3 !w-3 !rounded-full !border-2 !border-[#2a2a2a] !bg-[#0a0a0a] hover:!border-[#ff6d35] transition-colors"
          style={{ left: -6 }}
        />
      )}

      {/* Header */}
      <div
        className="flex items-center gap-2 rounded-t-xl px-3 py-2.5"
        style={{ background: `${color}18`, borderBottom: `1px solid ${color}30` }}
      >
        {icon && (
          <div
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md"
            style={{ background: `${color}30` }}
          >
            <span className="text-xs" style={{ color }}>{icon}</span>
          </div>
        )}
        <span className="flex-1 truncate text-xs font-semibold text-gray-200">
          {(d.label as string) ?? label ?? (d.type_slug as string) ?? 'Node'}
        </span>
        {Boolean(d.pinned) && <Pin className="h-3 w-3 text-amber-400" />}
        {statusIcon}
      </div>

      {/* Body */}
      {children && (
        <div className="px-3 py-2 text-xs text-gray-500">
          {children}
        </div>
      )}

      {/* Output handle */}
      {showOutputHandle && (
        <Handle
          type="source"
          position={Position.Right}
          className="!h-3 !w-3 !rounded-full !border-2 !border-[#2a2a2a] !bg-[#0a0a0a] hover:!border-[#ff6d35] transition-colors"
          style={{ right: -6 }}
        />
      )}
    </div>
  )
})

BaseNode.displayName = 'BaseNode'
