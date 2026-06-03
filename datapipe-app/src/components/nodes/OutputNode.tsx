'use client'

import { memo } from 'react'
import { type NodeProps } from '@xyflow/react'
import { Download, BarChart3, Table2 } from 'lucide-react'
import { BaseNode } from './BaseNode'
import type { ExportConfig, ChartConfig, TablePreviewConfig } from '@/types/nodeConfigs'

// ── Table Preview ─────────────────────────────────────────────────────────
export const TablePreviewNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as TablePreviewConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined

  return (
    <BaseNode {...props} color="#f59e0b" icon={<Table2 className="h-3.5 w-3.5" />} showOutputHandle={false}>
      <div className="space-y-0.5">
        <span className="text-amber-400 text-[10px]">
          {cfg?.page_size ? `${cfg.page_size} lignes/page` : 'Pagination par défaut'}
        </span>
        {preview?.message && (
          <span className="text-[10px] text-amber-300 block">{preview.message}</span>
        )}
      </div>
    </BaseNode>
  )
})
TablePreviewNode.displayName = 'TablePreviewNode'

// ── Chart ─────────────────────────────────────────────────────────────────
export const ChartNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as ChartConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined

  const chartLabels: Record<string, string> = {
    bar: 'Barres', line: 'Ligne', pie: 'Camembert', area: 'Aires',
  }

  return (
    <BaseNode {...props} color="#f59e0b" icon={<BarChart3 className="h-3.5 w-3.5" />} showOutputHandle={false}>
      {cfg?.chart_type && cfg?.x_axis ? (
        <div className="space-y-0.5">
          <span className="text-amber-400 text-[10px]">
            {chartLabels[cfg.chart_type]} · X={cfg.x_axis} Y={cfg.y_axis ?? '?'}
          </span>
          {cfg.title && <span className="text-gray-600 text-[10px] italic">{cfg.title}</span>}
          {preview?.message && (
            <span className="text-[10px] text-amber-300 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-gray-600 italic">Configurez les axes</span>
      )}
    </BaseNode>
  )
})
ChartNode.displayName = 'ChartNode'

// ── Export ────────────────────────────────────────────────────────────────
export const ExportNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as ExportConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string; file_size?: string } | undefined

  return (
    <BaseNode {...props} color="#f59e0b" icon={<Download className="h-3.5 w-3.5" />} showOutputHandle={false}>
      {cfg?.format ? (
        <div className="space-y-0.5">
          <span className="text-amber-400 uppercase font-mono text-xs">{cfg.format}</span>
          {cfg.filename && <span className="text-gray-600 text-[10px] truncate block">{cfg.filename}</span>}
          {preview?.message && (
            <span className="text-[10px] text-amber-300 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-gray-600 italic">Format non défini</span>
      )}
    </BaseNode>
  )
})
ExportNode.displayName = 'ExportNode'
