'use client'

import { useState, useEffect } from 'react'
import { X, Trash2, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { useEditorStore } from '@/store/editor.store'
import { nodeService } from '@/services/node.service'
import { fileService } from '@/services/file.service'
import { aiService } from '@/services/ai.service'
import { toast } from 'sonner'
import { NODE_REGISTRY_MAP } from '@/lib/nodeRegistry'

// Per-node inspector panels
import { InspectorCSVImport } from './inspector/InspectorCSVImport'
import { InspectorJSONLoader } from './inspector/InspectorJSONLoader'
import { InspectorSQLQuery } from './inspector/InspectorSQLQuery'
import { InspectorFilter } from './inspector/InspectorFilter'
import { InspectorJoin } from './inspector/InspectorJoin'
import { InspectorAggregate } from './inspector/InspectorAggregate'
import { InspectorRename } from './inspector/InspectorRename'
import { InspectorClean } from './inspector/InspectorClean'
import { InspectorAITransform } from './inspector/InspectorAITransform'
import { InspectorTablePreview } from './inspector/InspectorTablePreview'
import { InspectorChart } from './inspector/InspectorChart'
import { InspectorExport } from './inspector/InspectorExport'

interface NodeInspectorProps {
  pipelineId: string
}

export function NodeInspector({ pipelineId }: NodeInspectorProps) {
  const { selectedNodeId, nodes, setSelectedNode, setNodes, edges, setEdges } = useEditorStore()
  const [config, setConfig] = useState<Record<string, unknown>>({})
  const [label, setLabel] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [files, setFiles] = useState<Array<{ id: string; name: string; rows?: number; columns?: number; format?: string }>>([])

  const selectedNode = nodes.find((n) => n.id === selectedNodeId)
  const typeSlug = selectedNode ? ((selectedNode.data as Record<string, unknown>).type_slug as string ?? selectedNode.type) : null
  const typeDef = typeSlug ? NODE_REGISTRY_MAP[typeSlug] : null

  // Load files for source nodes
  useEffect(() => {
    if (!typeSlug || !['csv_import', 'json_loader'].includes(typeSlug)) return
    fileService.list().then(setFiles).catch(() => {})
  }, [typeSlug])

  useEffect(() => {
    if (!selectedNode) return
    const d = selectedNode.data as Record<string, unknown>
    setConfig((d.config as Record<string, unknown>) ?? {})
    setLabel((d.label as string) ?? typeDef?.label ?? '')
  }, [selectedNodeId])

  if (!selectedNode || !typeSlug) return null

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await nodeService.updateNode(pipelineId, selectedNode.id, {
        'data.config': config,
        'data.label': label,
      })
      setNodes(nodes.map((n) =>
        n.id === selectedNode.id
          ? { ...n, data: { ...n.data, config, label } }
          : n
      ))
      toast.success('Nœud mis à jour')
    } catch {
      toast.error('Erreur lors de la mise à jour')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    try {
      const result = await nodeService.deleteNode(pipelineId, selectedNode.id)
      setNodes(nodes.filter((n) => n.id !== selectedNode.id))
      setEdges(edges.filter((e) => !(result.deleted_edges ?? []).includes(e.id)))
      setSelectedNode(null)
      toast.success('Nœud supprimé')
    } catch {
      toast.error('Erreur lors de la suppression')
    }
  }

  const handleGenerateAICode = async (prompt: string, model: string): Promise<string> => {
    const res = await aiService.generateCode(prompt, { model })
    return res.code
  }

  // Columns from connected upstream node (placeholder — real impl via run preview)
  const upstreamColumns: string[] = (selectedNode.data as Record<string, unknown>).upstream_columns as string[] ?? []
  const csvFiles = files.filter(f => !f.format || f.format === 'csv')
  const jsonFiles = files.filter(f => !f.format || f.format === 'json')

  const renderConfigPanel = () => {
    const cfg = config as Record<string, unknown>
    switch (typeSlug) {
      case 'csv_import':
        return <InspectorCSVImport config={cfg as never} files={csvFiles} onChange={(c) => setConfig(c as never)} />
      case 'json_loader':
        return <InspectorJSONLoader config={cfg as never} files={jsonFiles} onChange={(c) => setConfig(c as never)} />
      case 'sql_query':
        return <InspectorSQLQuery config={cfg as never} onChange={(c) => setConfig(c as never)} />
      case 'filter':
        return <InspectorFilter config={cfg as never} columns={upstreamColumns} onChange={(c) => setConfig(c as never)} />
      case 'join':
        return <InspectorJoin config={cfg as never} leftColumns={upstreamColumns} rightColumns={[]} onChange={(c) => setConfig(c as never)} />
      case 'aggregate':
        return <InspectorAggregate config={cfg as never} columns={upstreamColumns} onChange={(c) => setConfig(c as never)} />
      case 'rename':
        return <InspectorRename config={cfg as never} columns={upstreamColumns} onChange={(c) => setConfig(c as never)} />
      case 'clean':
        return <InspectorClean config={cfg as never} onChange={(c) => setConfig(c as never)} />
      case 'ai_transform':
        return <InspectorAITransform config={cfg as never} onChange={(c) => setConfig(c as never)} onGenerateCode={handleGenerateAICode} />
      case 'table_preview':
        return <InspectorTablePreview config={cfg as never} columns={upstreamColumns} onChange={(c) => setConfig(c as never)} />
      case 'chart':
        return <InspectorChart config={cfg as never} columns={upstreamColumns} onChange={(c) => setConfig(c as never)} />
      case 'export':
        return <InspectorExport config={cfg as never} onChange={(c) => setConfig(c as never)} />
      default:
        return <p className="text-xs text-slate-500 italic">Pas de configuration pour ce nœud</p>
    }
  }

  return (
    <aside className="flex h-full w-[300px] flex-col border-l border-[#e6e8ec] bg-[#eaedf2]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#e6e8ec] px-4 py-3">
        <div className="flex items-center gap-2">
          {typeDef && (
            <span className="text-lg leading-none" style={{ color: typeDef.color }}>{typeDef.icon}</span>
          )}
          <span className="text-sm font-semibold text-slate-800">{typeDef?.label ?? typeSlug}</span>
        </div>
        <Button variant="ghost" size="icon-sm" onClick={() => setSelectedNode(null)}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* Label */}
          <div className="space-y-1.5">
            <Label htmlFor="node-label">Label affiché</Label>
            <Input
              id="node-label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder={typeDef?.label}
            />
          </div>

          <Separator />

          {/* Config panel */}
          <div className="space-y-1.5">
            <Label className="text-[10px] uppercase tracking-widest text-gray-700">Configuration</Label>
            {renderConfigPanel()}
          </div>
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t border-[#e6e8ec] p-3 flex items-center gap-2">
        <Button size="sm" onClick={handleSave} disabled={isSaving} className="flex-1 gap-1.5">
          <Save className="h-3.5 w-3.5" />
          {isSaving ? 'Sauvegarde…' : 'Sauvegarder'}
        </Button>
        <Button size="icon-sm" variant="ghost" onClick={handleDelete} className="text-red-400 hover:text-red-300">
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </aside>
  )
}
