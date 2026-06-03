'use client'

import { memo } from 'react'
import { type NodeProps } from '@xyflow/react'
import { Filter, GitMerge, BarChart2, Columns, Eraser } from 'lucide-react'
import { BaseNode } from './BaseNode'
import type { FilterConfig, JoinConfig, AggregateConfig, RenameConfig, CleanConfig } from '@/types/nodeConfigs'

// ── Filtre ────────────────────────────────────────────────────────────────
export const FilterNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as FilterConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined

  return (
    <BaseNode {...props} color="#3b82f6" icon={<Filter className="h-3.5 w-3.5" />}>
      {cfg?.column ? (
        <div className="space-y-0.5">
          <span className="text-blue-400 font-mono text-[10px]">
            {cfg.column} {cfg.operator ?? '=='} {cfg.value ?? '…'}
          </span>
          {preview?.message && (
            <span className="text-[10px] text-blue-300 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-slate-500 italic">Non configuré</span>
      )}
    </BaseNode>
  )
})
FilterNode.displayName = 'FilterNode'

// ── Join ─────────────────────────────────────────────────────────────────
export const JoinNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as JoinConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined

  return (
    <BaseNode {...props} color="#3b82f6" icon={<GitMerge className="h-3.5 w-3.5" />}>
      {cfg?.left_key ? (
        <div className="space-y-0.5">
          <span className="text-blue-400 font-mono text-[10px]">
            {cfg.join_type ?? 'LEFT'} · {cfg.left_key} = {cfg.right_key}
          </span>
          {preview?.message && (
            <span className="text-[10px] text-blue-300 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-slate-500 italic">Non configuré</span>
      )}
    </BaseNode>
  )
})
JoinNode.displayName = 'JoinNode'

// ── Agrégation ────────────────────────────────────────────────────────────
export const AggregateNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as AggregateConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined

  return (
    <BaseNode {...props} color="#3b82f6" icon={<BarChart2 className="h-3.5 w-3.5" />}>
      {cfg?.group_by?.length ? (
        <div className="space-y-0.5">
          <span className="text-blue-400 text-[10px]">
            GROUP BY {cfg.group_by.slice(0, 2).join(', ')}{cfg.group_by.length > 2 ? '…' : ''}
          </span>
          {cfg.aggregations?.length ? (
            <span className="text-slate-500 text-[10px]">
              {cfg.aggregations.slice(0, 2).map(a => `${a.function}(${a.column})`).join(', ')}
            </span>
          ) : null}
          {preview?.message && (
            <span className="text-[10px] text-blue-300 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-slate-500 italic">Non configuré</span>
      )}
    </BaseNode>
  )
})
AggregateNode.displayName = 'AggregateNode'

// ── Rename / Select ───────────────────────────────────────────────────────
export const RenameNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as RenameConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined
  const opCount = cfg?.operations?.length ?? 0

  return (
    <BaseNode {...props} color="#3b82f6" icon={<Columns className="h-3.5 w-3.5" />}>
      {opCount > 0 ? (
        <div className="space-y-0.5">
          <span className="text-blue-400 text-[10px]">{opCount} opération{opCount > 1 ? 's' : ''}</span>
          {preview?.message && (
            <span className="text-[10px] text-blue-300 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-slate-500 italic">Aucune opération</span>
      )}
    </BaseNode>
  )
})
RenameNode.displayName = 'RenameNode'

// ── Nettoyage ────────────────────────────────────────────────────────────
export const CleanNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as CleanConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined

  const activeOps = [
    cfg?.remove_duplicates && 'dédupliquer',
    cfg?.drop_null_rows && 'sup. nulls',
    cfg?.trim_strings && 'trim',
  ].filter(Boolean)

  return (
    <BaseNode {...props} color="#3b82f6" icon={<Eraser className="h-3.5 w-3.5" />}>
      {activeOps.length > 0 ? (
        <div className="space-y-0.5">
          <span className="text-blue-400 text-[10px]">{activeOps.join(' · ')}</span>
          {preview?.message && (
            <span className="text-[10px] text-blue-300 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-slate-500 italic">Non configuré</span>
      )}
    </BaseNode>
  )
})
CleanNode.displayName = 'CleanNode'
