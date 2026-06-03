'use client'

import { useEffect, useState } from 'react'
import { ReactFlowProvider } from '@xyflow/react'
import { useEditorStore } from '@/store/editor.store'
import { pipelineService } from '@/services/pipeline.service'
import { nodeService } from '@/services/node.service'
import { DEMO_PIPELINES_DATA } from '@/lib/demoPipelines'
import { EditorTopBar } from './EditorTopBar'
import { NodeDrawer } from './NodeDrawer'
import { EditorCanvas } from './EditorCanvas'
import { NodeInspector } from './NodeInspector'
import { RunConsole } from './RunConsole'
import { AIChatPanel } from './AIChatPanel'
import { Skeleton } from '@/components/ui/skeleton'

interface PipelineEditorProps {
  pipelineId: string
}

export function PipelineEditor({ pipelineId }: PipelineEditorProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [consoleHeight, setConsoleHeight] = useState(220)

  const {
    setPipeline, setNodeTypes,
    isInspectorOpen, isConsoleOpen, setConsoleOpen, isAIChatOpen,
  } = useEditorStore()

  useEffect(() => {
    const load = async () => {
      try {
        // Demo pipelines: load mock data without API
        if (pipelineId.startsWith('demo-')) {
          const mock = DEMO_PIPELINES_DATA[pipelineId]
          if (mock) {
            setPipeline(mock.pipeline)
            setNodeTypes(mock.nodeTypes)
            useEditorStore.getState().setNodes(mock.nodes)
            useEditorStore.getState().setEdges(mock.edges)
          }
          setIsLoading(false)
          return
        }
        const [pipeline, nodeTypes] = await Promise.all([
          pipelineService.get(pipelineId),
          nodeService.getNodeTypes(),
        ])
        setPipeline(pipeline)
        setNodeTypes(nodeTypes)
      } catch (e) {
        console.error(e)
      } finally {
        setIsLoading(false)
      }
    }
    load()
    // Reset run state on mount
    useEditorStore.getState().resetRun()
    return () => {
      useEditorStore.getState().resetRun()
    }
  }, [pipelineId, setPipeline, setNodeTypes])

  if (isLoading) {
    return (
      <div className="flex h-full w-full flex-col bg-[#0a0a0a]">
        <div className="h-12 border-b border-[#1e1e1e] bg-[#0a0a0a]" />
        <div className="flex flex-1 overflow-hidden">
          <div className="flex-1 p-8 space-y-4">
            <Skeleton className="h-32 w-48 rounded-xl" />
            <Skeleton className="h-32 w-48 rounded-xl ml-64" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <ReactFlowProvider>
      <div className="flex h-full w-full flex-col overflow-hidden bg-[#0a0a0a]">
        {/* Top bar */}
        <EditorTopBar pipelineId={pipelineId} />

        {/* Main area */}
        <div className="flex flex-1 overflow-hidden">
          {/* Center + bottom */}
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Canvas — relative pour que NodeDrawer soit contenu dedans */}
            <div className="relative flex-1 overflow-hidden">
              <EditorCanvas pipelineId={pipelineId} />
              <NodeDrawer pipelineId={pipelineId} />
            </div>

            {/* Console */}
            {isConsoleOpen && (
              <RunConsole
                height={consoleHeight}
                onClose={() => setConsoleOpen(false)}
                onResize={(delta) => setConsoleHeight((h) => Math.max(120, Math.min(500, h + delta)))}
              />
            )}
          </div>

          {/* Right: inspector */}
          {isInspectorOpen && (
            <NodeInspector pipelineId={pipelineId} />
          )}
        </div>

        {/* Floating AI panel */}
        {isAIChatOpen && <AIChatPanel pipelineId={pipelineId} />}
      </div>
    </ReactFlowProvider>
  )
}
