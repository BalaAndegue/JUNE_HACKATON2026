'use client'

import { useCallback, useEffect } from 'react'
import {
  ReactFlow, Background, MiniMap, Panel, BackgroundVariant,
  type OnConnect, type NodeTypes, addEdge,
  type Node as RFNode,
} from '@xyflow/react'
import { CanvasControls } from './CanvasControls'
import '@xyflow/react/dist/style.css'
import { useEditorStore } from '@/store/editor.store'
import { nodeService } from '@/services/node.service'
import { NODE_REGISTRY } from '@/lib/nodeRegistry'
import { toast } from 'sonner'

// Sources
import { CSVImportNode, JSONLoaderNode, SQLSourceNode } from '@/components/nodes/SourceNode'
// Transforms
import { FilterNode, JoinNode, AggregateNode, RenameNode, CleanNode } from '@/components/nodes/TransformNode'
// AI
import { AITransformNode } from '@/components/nodes/AINode'
// Outputs
import { TablePreviewNode, ChartNode, ExportNode } from '@/components/nodes/OutputNode'
// Fallback
import { GenericNode } from '@/components/nodes/GenericNode'

const nodeTypes: NodeTypes = {
  csv_import: CSVImportNode,
  json_loader: JSONLoaderNode,
  sql_query: SQLSourceNode,
  filter: FilterNode,
  join: JoinNode,
  aggregate: AggregateNode,
  rename: RenameNode,
  clean: CleanNode,
  ai_transform: AITransformNode,
  table_preview: TablePreviewNode,
  chart: ChartNode,
  export: ExportNode,
  default: GenericNode,
}

interface EditorCanvasProps {
  pipelineId: string
}

export function EditorCanvas({ pipelineId }: EditorCanvasProps) {
  const { nodes, edges, onNodesChange, onEdgesChange, setEdges, setNodeTypes } = useEditorStore()

  // Seed the store with registry so NodePanel + GenericNode can read it
  useEffect(() => {
    setNodeTypes(NODE_REGISTRY)
  }, [setNodeTypes])

  const onConnect: OnConnect = useCallback(
    async (connection) => {
      if (!connection.source || !connection.target) return
      try {
        const validation = await nodeService.validateEdge(pipelineId, {
          source: connection.source,
          target: connection.target,
        })
        if (!validation.valid) {
          toast.error(validation.reason ?? 'Connexion invalide')
          return
        }
        const edge = await nodeService.createEdge(pipelineId, {
          source: connection.source,
          target: connection.target,
          source_handle: connection.sourceHandle ?? undefined,
          target_handle: connection.targetHandle ?? undefined,
        })
        setEdges(addEdge({ ...connection, id: edge.id }, edges))
      } catch {
        toast.error('Erreur lors de la connexion')
      }
    },
    [pipelineId, edges, setEdges]
  )

  const onNodeDragStop = useCallback(
    async (_event: unknown, node: RFNode) => {
      try {
        await nodeService.updateNode(pipelineId, node.id, { position: node.position })
      } catch {}
    },
    [pipelineId]
  )

  // Drop from node panel
  const onDrop = useCallback(
    async (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      const typeSlug = e.dataTransfer.getData('application/reactflow-type')
      const labelText = e.dataTransfer.getData('application/reactflow-label')
      if (!typeSlug) return

      const bounds = (e.currentTarget as HTMLElement).getBoundingClientRect()
      const position = { x: e.clientX - bounds.left - 90, y: e.clientY - bounds.top - 20 }

      try {
        const { setNodes, nodes: currentNodes } = useEditorStore.getState()
        const node = await nodeService.addNode(pipelineId, {
          type: typeSlug,
          position,
          data: { config: {} },
          label: labelText,
        })
        setNodes([
          ...currentNodes,
          {
            id: node.id,
            type: typeSlug,
            position: node.position,
            data: { ...node.data, type_slug: typeSlug },
          },
        ])
        toast.success(`"${labelText}" ajouté`)
      } catch {
        toast.error("Erreur lors de l'ajout")
      }
    },
    [pipelineId]
  )

  return (
    <div
      className="h-full w-full"
      style={{ background: '#06060a' }}
      onDrop={onDrop}
      onDragOver={(e) => e.preventDefault()}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeDragStop={onNodeDragStop}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        defaultEdgeOptions={{
          style: { stroke: '#2a2a2a', strokeWidth: 2 },
          animated: false,
        }}
        proOptions={{ hideAttribution: true }}
        // Empêche le scroll de la page quand la souris est sur le canvas
        preventScrolling
        panOnScroll={false}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1.5} color="rgba(255,255,255,0.25)" />
        <MiniMap className="border-[#2a2a2a]! bg-[#0a0a0a]!" nodeColor="#1e1e1e" maskColor="rgba(0,0,0,0.5)" />
        {/* Barre de contrôles custom — Panel React Flow pour rester dans le canvas */}
        <Panel position="bottom-center" style={{ margin: 0, width: '100%', pointerEvents: 'none' }}>
          <CanvasControls pipelineId={pipelineId} />
        </Panel>
      </ReactFlow>
    </div>
  )
}
