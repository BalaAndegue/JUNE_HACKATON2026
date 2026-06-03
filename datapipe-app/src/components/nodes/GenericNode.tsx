'use client'

import { memo } from 'react'
import { type NodeProps } from '@xyflow/react'
import { Box } from 'lucide-react'
import { BaseNode } from './BaseNode'
import { useEditorStore } from '@/store/editor.store'
import { getCategoryColor } from '@/lib/utils'

export const GenericNode = memo((props: NodeProps) => {
  const nodeTypes = useEditorStore((s) => s.nodeTypes)
  const typeSlug = (props.data as Record<string, unknown>).type_slug as string | undefined
  const typeDef = nodeTypes.find((t) => t.slug === typeSlug)
  const color = typeDef ? getCategoryColor(typeDef.category) : '#6b7280'

  return (
    <BaseNode {...props} color={color} icon={<Box className="h-3.5 w-3.5" />}>
      <span className="text-gray-600 italic text-[10px]">{typeDef?.label ?? typeSlug}</span>
    </BaseNode>
  )
})
GenericNode.displayName = 'GenericNode'
