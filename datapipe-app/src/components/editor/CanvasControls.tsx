'use client'

import { useCallback, useState } from 'react'
import { useReactFlow } from '@xyflow/react'
import {
  ZoomIn, ZoomOut, Maximize2, Play, Square, Loader2,
} from 'lucide-react'
import { useEditorStore } from '@/store/editor.store'
import { runService } from '@/services/run.service'
import { pipelineService } from '@/services/pipeline.service'
import { toast } from 'sonner'
import { useAuthStore } from '@/store/auth.store'

interface CanvasControlsProps {
  pipelineId: string
}

// Un bouton de la barre zoom
function CtrlBtn({
  onClick, children, title,
}: {
  onClick: () => void
  children: React.ReactNode
  title: string
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-white/8 hover:text-gray-200 active:scale-95"
      style={{ border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)' }}
    >
      {children}
    </button>
  )
}

export function CanvasControls({ pipelineId }: CanvasControlsProps) {
  const { zoomIn, zoomOut, fitView } = useReactFlow()
  const { isDemoMode } = useAuthStore()

  const {
    nodes, edges, isRunning, runStatus,
    activeRunId, setActiveRun, setRunStatus, setNodeStatus,
    appendLog, resetRun,
  } = useEditorStore()

  const handleRun = useCallback(async () => {
    if (isDemoMode) {
      toast.info('Mode démo — connectez une API pour exécuter')
      return
    }
    try {
      const result = await runService.execute(pipelineId)
      setActiveRun(result.run_id)
      setRunStatus('queued')

      const ws = new WebSocket(
        `${process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000'}/ws/runs/${result.run_id}`
      )
      ws.onmessage = (e) => {
        const event = JSON.parse(e.data)
        if (event.type === 'node_status') setNodeStatus(event.node_id, event.status)
        else if (event.type === 'run_complete') {
          setRunStatus(event.status)
          ws.close()
          toast.success(event.status === 'success' ? 'Run terminé' : 'Run échoué')
        }
      }

      runService.streamLogs(result.run_id, (log) => {
        appendLog(log)
        setRunStatus('running')
      })
    } catch {
      toast.error("Erreur lors de l'exécution")
      setRunStatus('failed')
    }
  }, [pipelineId, isDemoMode, setActiveRun, setRunStatus, setNodeStatus, appendLog])

  const handleCancel = useCallback(async () => {
    if (!activeRunId) return
    try {
      await runService.cancel(activeRunId)
      setRunStatus('cancelled')
      resetRun()
      toast.info('Run annulé')
    } catch {
      toast.error("Impossible d'annuler")
    }
  }, [activeRunId, setRunStatus, resetRun])

  const isQueued = runStatus === 'queued' || runStatus === 'running'

  return (
    <div className="flex w-full items-center justify-between px-4 pb-4 pointer-events-none">
      {/* Gauche — contrôles zoom, horizontal, espacés */}
      <div className="flex items-center gap-1.5 pointer-events-auto">
        <CtrlBtn onClick={() => fitView({ duration: 250, padding: 0.2 })} title="Ajuster la vue">
          <Maximize2 className="h-3.5 w-3.5" />
        </CtrlBtn>
        <CtrlBtn onClick={() => zoomOut({ duration: 200 })} title="Dézoomer">
          <ZoomOut className="h-3.5 w-3.5" />
        </CtrlBtn>
        <CtrlBtn onClick={() => zoomIn({ duration: 200 })} title="Zoomer">
          <ZoomIn className="h-3.5 w-3.5" />
        </CtrlBtn>
      </div>

      {/* Centre — bouton Exécuter */}
      <div className="pointer-events-auto">
        {isQueued ? (
          <button
            onClick={handleCancel}
            className="flex items-center gap-2 rounded-xl px-5 py-2 text-sm font-semibold text-white transition-all active:scale-95"
            style={{ background: '#dc2626', border: '1px solid rgba(220,38,38,0.5)', boxShadow: '0 4px 16px rgba(220,38,38,0.25)' }}
          >
            <Loader2 className="h-4 w-4 animate-spin" />
            Arrêter
          </button>
        ) : (
          <button
            onClick={handleRun}
            className="flex items-center gap-2 rounded-xl px-5 py-2 text-sm font-semibold text-white transition-all hover:brightness-110 active:scale-95"
            style={{ background: '#ff6d35', border: '1px solid rgba(255,109,53,0.4)', boxShadow: '0 4px 20px rgba(255,109,53,0.3)' }}
          >
            <Play className="h-4 w-4" fill="currentColor" />
            Exécuter
          </button>
        )}
      </div>

      {/* Droite — espace symétrique */}
      <div className="w-28" />
    </div>
  )
}
