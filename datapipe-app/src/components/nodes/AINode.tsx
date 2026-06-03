'use client'

import { memo } from 'react'
import { type NodeProps } from '@xyflow/react'
import { Sparkles, Code2 } from 'lucide-react'
import { BaseNode } from './BaseNode'
import type { AITransformConfig } from '@/types/nodeConfigs'

export const AITransformNode = memo((props: NodeProps) => {
  const cfg = (props.data as Record<string, unknown>).config as AITransformConfig | undefined
  const preview = (props.data as Record<string, unknown>).preview as { message?: string } | undefined

  return (
    <BaseNode {...props} color="#a855f7" icon={<Sparkles className="h-3.5 w-3.5" />}>
      {cfg?.prompt ? (
        <div className="space-y-1">
          <span className="text-purple-400 italic text-[10px] line-clamp-2">
            {cfg.prompt.slice(0, 60)}{cfg.prompt.length > 60 ? '…' : ''}
          </span>
          {cfg.generated_code && (
            <div className="flex items-center gap-1 text-[9px] text-gray-600">
              <Code2 className="h-2.5 w-2.5" />
              Code généré
            </div>
          )}
          {preview?.message && (
            <span className="text-[10px] text-purple-300 block">{preview.message}</span>
          )}
        </div>
      ) : (
        <span className="text-gray-600 italic">Décrivez la transformation en français…</span>
      )}
    </BaseNode>
  )
})
AITransformNode.displayName = 'AITransformNode'
