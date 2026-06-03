'use client'

import { useState, useMemo } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useEditorStore } from '@/store/editor.store'
import { nodeService } from '@/services/node.service'
import { NODE_REGISTRY } from '@/lib/nodeRegistry'
import { getCategoryColor } from '@/lib/utils'
import { toast } from 'sonner'
import type { NodeType } from '@/types'

const CATEGORY_LABELS: Record<string, string> = {
  source: 'Sources',
  transform: 'Transformations',
  ai: 'IA',
  output: 'Sorties',
}

const CATEGORY_ORDER = ['source', 'transform', 'ai', 'output']

interface NodePanelProps {
  pipelineId: string
}

export function NodePanel({ pipelineId }: NodePanelProps) {
  const [search, setSearch] = useState('')
  const { setNodes, nodes } = useEditorStore()

  const filtered = useMemo(() => {
    if (!search) return NODE_REGISTRY
    const q = search.toLowerCase()
    return NODE_REGISTRY.filter(
      (t) => t.label.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
    )
  }, [search])

  const grouped = useMemo(() => {
    const g: Record<string, NodeType[]> = {}
    filtered.forEach((t) => {
      if (!g[t.category]) g[t.category] = []
      g[t.category].push(t)
    })
    return g
  }, [filtered])

  const handleDoubleClick = async (type: NodeType) => {
    const x = 200 + Math.random() * 80
    const y = 150 + Object.keys(nodes).length * 40
    try {
      const node = await nodeService.addNode(pipelineId, {
        type: type.slug,
        position: { x, y },
        data: { config: {} },
        label: type.label,
      })
      setNodes([
        ...nodes,
        { id: node.id, type: type.slug, position: node.position, data: { ...node.data, type_slug: type.slug } },
      ])
      toast.success(`"${type.label}" ajouté`)
    } catch {
      toast.error("Erreur lors de l'ajout")
    }
  }

  const handleDragStart = (e: React.DragEvent, type: NodeType) => {
    e.dataTransfer.setData('application/reactflow-type', type.slug)
    e.dataTransfer.setData('application/reactflow-label', type.label)
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <aside className="flex h-full w-55 flex-col border-r border-[#e6e8ec] bg-[#f4f6f9]">
      {/* Header */}
      <div className="border-b border-[#e6e8ec] p-3">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-700">Nœuds</p>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
          <Input className="h-7 pl-7 text-xs" placeholder="Rechercher…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-2 space-y-4">
          {CATEGORY_ORDER.filter((cat) => grouped[cat]?.length).map((cat) => (
            <div key={cat}>
              <p className="mb-1 px-2 text-[10px] font-bold uppercase tracking-widest text-gray-700">
                {CATEGORY_LABELS[cat] ?? cat}
              </p>
              {grouped[cat].map((type) => (
                <div
                  key={type.slug}
                  className="group flex items-center gap-2.5 rounded-lg px-2 py-2 cursor-grab transition-colors hover:bg-[#ffffff] active:cursor-grabbing"
                  draggable
                  onDragStart={(e) => handleDragStart(e, type)}
                  onDoubleClick={() => handleDoubleClick(type)}
                  title={`Double-clic ou glisser pour ajouter\n${type.description}`}
                >
                  <div
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[13px]"
                    style={{
                      background: `${type.color}18`,
                      border: `1px solid ${type.color}30`,
                    }}
                  >
                    {type.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-xs font-medium text-slate-600 group-hover:text-slate-800 transition-colors">
                      {type.label}
                    </p>
                    <p className="truncate text-[10px] text-gray-700">{type.description}</p>
                  </div>
                </div>
              ))}
            </div>
          ))}

          {filtered.length === 0 && (
            <p className="px-3 py-6 text-center text-xs text-slate-500">Aucun résultat</p>
          )}
        </div>
      </ScrollArea>
    </aside>
  )
}
