'use client'

import { useState, useMemo } from 'react'
import { Plus, Search, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { useEditorStore } from '@/store/editor.store'
import { nodeService } from '@/services/node.service'
import { NODE_REGISTRY } from '@/lib/nodeRegistry'
import { toast } from 'sonner'
import type { NodeType } from '@/types'

const CATEGORY_ORDER = ['source', 'transform', 'ai', 'output']
const CATEGORY_LABELS: Record<string, string> = {
  source: 'Sources',
  transform: 'Transformations',
  ai: 'IA',
  output: 'Sorties',
}

interface NodeDrawerProps {
  pipelineId: string
}

export function NodeDrawer({ pipelineId }: NodeDrawerProps) {
  const [open, setOpen] = useState(false)
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

  const handleAdd = async (type: NodeType) => {
    const x = 200 + Math.random() * 80
    const y = 150 + nodes.length * 40
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
      const localNode = {
        id: `local-${Date.now()}`,
        type: type.slug,
        position: { x, y },
        data: { label: type.label, config: {}, type_slug: type.slug },
      }
      setNodes([...nodes, localNode])
      toast.success(`"${type.label}" ajouté`)
    }
  }

  const handleDragStart = (e: React.DragEvent, type: NodeType) => {
    e.dataTransfer.setData('application/reactflow-type', type.slug)
    e.dataTransfer.setData('application/reactflow-label', type.label)
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <>
      {/* Bouton + — carré, en haut à droite du canvas */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="absolute top-3 right-3 z-20 flex h-8 w-8 items-center justify-center rounded-lg transition-all duration-150 hover:bg-slate-900/10 active:scale-95"
        style={{
          background: open ? 'rgba(15,23,42,0.10)' : 'rgba(15,23,42,0.07)',
          border: '1px solid rgba(255,255,255,0.12)',
        }}
        title="Ajouter un nœud"
      >
        {open
          ? <X className="h-3.5 w-3.5 text-slate-600" />
          : <Plus className="h-3.5 w-3.5 text-slate-600" strokeWidth={2} />
        }
      </button>

      {/* Drawer — absolute, limité à la zone canvas, sans overlay ni blur */}
      <div
        className="absolute top-0 right-0 z-10 flex flex-col"
        style={{
          width: 260,
          height: '100%',
          background: '#eaedf2',
          borderLeft: '1px solid rgba(15,23,42,0.07)',
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.22s cubic-bezier(0.16,1,0.3,1)',
          boxShadow: '-12px 0 40px rgba(0,0,0,0.35)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-3"
          style={{ borderBottom: '1px solid rgba(15,23,42,0.07)' }}
        >
          <p className="text-xs font-semibold text-slate-700">Nœuds</p>
          <button
            onClick={() => setOpen(false)}
            className="flex h-6 w-6 items-center justify-center rounded-md text-slate-500 hover:bg-slate-900/[0.06] hover:text-slate-700 transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Search */}
        <div className="px-3 py-2" style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3 w-3 -translate-y-1/2 text-slate-500" />
            <Input
              className="h-7 pl-8 text-xs"
              placeholder="Rechercher…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus={open}
            />
          </div>
        </div>

        {/* Node list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-3">
          {CATEGORY_ORDER.filter((cat) => grouped[cat]?.length).map((cat) => (
            <div key={cat}>
              <p className="mb-1 px-2 text-[9px] font-bold uppercase tracking-widest text-gray-700">
                {CATEGORY_LABELS[cat]}
              </p>
              {grouped[cat].map((type) => (
                <div
                  key={type.slug}
                  draggable
                  onDragStart={(e) => handleDragStart(e, type)}
                  onClick={() => handleAdd(type)}
                  className="group flex items-center gap-3 rounded-lg px-3 py-2 cursor-pointer transition-colors hover:bg-slate-900/5"
                  title={type.description}
                >
                  {/* dot coloré — pas d'emoji */}
                  <div
                    className="h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ background: type.color }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-600 group-hover:text-slate-800 transition-colors truncate">
                      {type.label}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="px-4 py-2" style={{ borderTop: '1px solid rgba(15,23,42,0.06)' }}>
          <p className="text-[9px] text-gray-700">Cliquer · Glisser pour placer</p>
        </div>
      </div>
    </>
  )
}
