'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Play, Square, RotateCcw, Save, ChevronLeft, Zap,
  Clock, History, Sparkles, Terminal, CheckCircle2, XCircle, Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Tooltip, TooltipContent, TooltipTrigger,
} from '@/components/ui/tooltip'
import { useEditorStore } from '@/store/editor.store'
import { pipelineService } from '@/services/pipeline.service'
import { runService } from '@/services/run.service'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface EditorTopBarProps {
  pipelineId: string
}

export function EditorTopBar({ pipelineId }: EditorTopBarProps) {
  const router = useRouter()
  const [isSaving, setIsSaving] = useState(false)
  const {
    pipeline, nodes, edges, isDirty, isRunning, runStatus,
    activeRunId, setActiveRun, setRunStatus, setNodeStatus, appendLog,
    resetRun, isConsoleOpen, setConsoleOpen, setAIChatOpen,
  } = useEditorStore()

  const handleSave = async () => {
    if (!pipeline) return
    setIsSaving(true)
    try {
      await pipelineService.save(pipelineId, {
        nodes: nodes as unknown[],
        edges: edges as unknown[],
      })
      useEditorStore.getState().markClean()
      toast.success('Pipeline sauvegardé')
    } catch {
      toast.error('Erreur lors de la sauvegarde')
    } finally {
      setIsSaving(false)
    }
  }

  const handleRun = async () => {
    try {
      // Save first
      if (isDirty) await handleSave()
      const result = await runService.execute(pipelineId)
      setActiveRun(result.run_id)
      setRunStatus('queued')
      setConsoleOpen(true)

      // Open WebSocket for real-time updates
      const ws = new WebSocket(
        `${(process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000')}/ws/runs/${result.run_id}`
      )
      ws.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data)
          if (event.type === 'node_status') {
            setNodeStatus(event.node_id, event.status)
          } else if (event.type === 'run_complete') {
            setRunStatus(event.status)
            ws.close()
            toast[event.status === 'success' ? 'success' : 'error'](
              event.status === 'success' ? 'Run terminé avec succès' : 'Run échoué'
            )
          }
        } catch {}
      }

      // Also stream logs via SSE
      runService.streamLogs(result.run_id, (log) => {
        appendLog(log)
        setRunStatus('running')
      })

    } catch {
      toast.error('Erreur lors du lancement')
    }
  }

  const handleCancel = async () => {
    if (!activeRunId) return
    try {
      await runService.cancel(activeRunId)
      setRunStatus('cancelled')
      resetRun()
      toast.info('Run annulé')
    } catch {
      toast.error('Impossible d\'annuler')
    }
  }

  const statusIcon = runStatus === 'running' || runStatus === 'queued'
    ? <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" />
    : runStatus === 'success'
    ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
    : runStatus === 'failed'
    ? <XCircle className="h-3.5 w-3.5 text-red-400" />
    : null

  return (
    <div className="flex h-12 shrink-0 items-center justify-between border-b border-[#1e1e1e] bg-[#0a0a0a] px-4">
      {/* Left */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon-sm" onClick={() => router.push('/dashboard/pipelines')}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Separator orientation="vertical" className="h-5" />
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-[#ff6d35]/15">
            <Zap className="h-3.5 w-3.5 text-[#ff6d35]" />
          </div>
          <span className="text-sm font-semibold text-gray-200">{pipeline?.name}</span>
          {isDirty && (
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" title="Modifications non sauvegardées" />
          )}
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center gap-1.5">
        {statusIcon && (
          <div className="flex items-center gap-1.5 mr-1 text-xs text-gray-500">
            {statusIcon}
            <span className="capitalize">{runStatus}</span>
          </div>
        )}

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon-sm" onClick={() => setAIChatOpen(true)}>
              <Sparkles className="h-4 w-4 text-purple-400" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Assistant IA</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setConsoleOpen(!isConsoleOpen)}
              className={cn(isConsoleOpen && 'text-[#ff6d35]')}
            >
              <Terminal className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Console</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <History className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Historique des versions</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <Clock className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Planifications</TooltipContent>
        </Tooltip>

        <Separator orientation="vertical" className="h-5 mx-1" />

        <Button
          variant="outline"
          size="sm"
          onClick={handleSave}
          disabled={isSaving || !isDirty}
          className="gap-1.5"
        >
          <Save className="h-3.5 w-3.5" />
          {isSaving ? 'Sauvegarde…' : 'Sauvegarder'}
        </Button>

        {isRunning ? (
          <Button
            variant="destructive"
            size="sm"
            onClick={handleCancel}
            className="gap-1.5"
          >
            <Square className="h-3.5 w-3.5" />
            Arrêter
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={handleRun}
            className="gap-1.5 bg-emerald-600 hover:bg-emerald-600/90 text-white"
          >
            <Play className="h-3.5 w-3.5" fill="currentColor" />
            Exécuter
          </Button>
        )}
      </div>
    </div>
  )
}
