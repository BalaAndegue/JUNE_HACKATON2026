'use client'

import { memo } from 'react'
import { type NodeProps } from '@xyflow/react'
import { FileText, Braces, Database } from 'lucide-react'
import { BaseNode } from './BaseNode'
import type { CSVImportConfig, JSONLoaderConfig, SQLQueryConfig } from '@/types/nodeConfigs'

// ── CSV Import ────────────────────────────────────────────────────────────
export const CSVImportNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as CSVImportConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined

  return (
    <BaseNode {...props} color="#00e5a0" icon={<FileText className="h-3.5 w-3.5" />} showInputHandle={false}>
      {cfg?.file_name ? (
        <div className="space-y-0.5">
          <span className="truncate text-emerald-400 block">{cfg.file_name}</span>
          {cfg.separator && (
            <span className="text-[10px] text-gray-600">sep: {cfg.separator === '\t' ? 'tab' : cfg.separator}</span>
          )}
          {preview?.message && (
            <span className="text-[10px] text-emerald-500 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-gray-600 italic">Aucun fichier sélectionné</span>
      )}
    </BaseNode>
  )
})
CSVImportNode.displayName = 'CSVImportNode'

// ── JSON Loader ───────────────────────────────────────────────────────────
export const JSONLoaderNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as JSONLoaderConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined

  return (
    <BaseNode {...props} color="#00e5a0" icon={<Braces className="h-3.5 w-3.5" />} showInputHandle={false}>
      {cfg?.file_name || cfg?.url ? (
        <div className="space-y-0.5">
          <span className="truncate text-emerald-400 block">
            {cfg.source === 'url' ? cfg.url : cfg.file_name}
          </span>
          {cfg.root_path && (
            <span className="text-[10px] text-gray-600">racine: {cfg.root_path}</span>
          )}
          {preview?.message && (
            <span className="text-[10px] text-emerald-500 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-gray-600 italic">Aucune source configurée</span>
      )}
    </BaseNode>
  )
})
JSONLoaderNode.displayName = 'JSONLoaderNode'

// ── SQL Query ─────────────────────────────────────────────────────────────
export const SQLSourceNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as SQLQueryConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined

  return (
    <BaseNode {...props} color="#00e5a0" icon={<Database className="h-3.5 w-3.5" />} showInputHandle={false}>
      {cfg?.query ? (
        <div className="space-y-0.5">
          <span className="font-mono text-[10px] text-emerald-400 truncate block">
            {cfg.query.replace(/\s+/g, ' ').slice(0, 45)}…
          </span>
          {preview?.message && (
            <span className="text-[10px] text-emerald-500 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-gray-600 italic">Aucune requête</span>
      )}
    </BaseNode>
  )
})
SQLSourceNode.displayName = 'SQLSourceNode'
