'use client'

import { useState, useRef, useEffect } from 'react'
import { X, Send, Sparkles, Loader2, Zap, ShieldCheck, AlertTriangle, Check, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useEditorStore } from '@/store/editor.store'
import { aiService, type AgentResult, type PlanAction } from '@/services/ai.service'
import { nodeService } from '@/services/node.service'
import { runService } from '@/services/run.service'
import { pipelineService } from '@/services/pipeline.service'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types'

interface AIChatPanelProps {
  pipelineId: string
}

export function AIChatPanel({ pipelineId }: AIChatPanelProps) {
  const {
    setAIChatOpen, setNodes, setEdges, nodes,
    setActiveRun, setRunStatus, setNodeStatus, setNodeResults, applyLineage, activeRunId,
  } = useEditorStore()
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: "Bonjour ! Dites-moi ce que vous voulez faire (« masque les clients », « exécute le pipeline », « génère le total par type »…). Je propose l'action, vous confirmez, j'agis.",
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [agent, setAgent] = useState<AgentResult | null>(null)
  const [pending, setPending] = useState<PlanAction | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Find a source file in the current graph to dry-run the agent on real data.
  const sourceFileId = (() => {
    for (const n of nodes) {
      const cfg = (n.data as { config?: Record<string, unknown> })?.config
      if (cfg && typeof cfg.file_id === 'string') return cfg.file_id as string
    }
    return undefined
  })()

  const handleAgent = async () => {
    if (!input.trim() || isLoading) return
    const description = input.trim()
    setInput('')
    setAgent(null)
    setMessages((prev) => [...prev, { role: 'user', content: `🤖 Agent : ${description}` }])
    setIsLoading(true)
    try {
      const result = await aiService.agentTransform(description, sourceFileId)
      setAgent(result)
    } catch {
      toast.error("L'agent n'a pas pu générer la transformation")
    } finally {
      setIsLoading(false)
    }
  }

  const applyAgent = async () => {
    if (!agent) return
    try {
      const node = await nodeService.addNode(pipelineId, {
        type: 'sql_transform',
        position: { x: 700, y: 360 },
        data: { config: { query: agent.generated_sql } },
        label: 'Transformation IA',
      })
      setNodes([
        ...nodes,
        { id: node.id, type: 'sql_transform', position: node.position,
          data: { ...node.data, type_slug: 'sql_transform' } } as unknown as import('@xyflow/react').Node,
      ])
      toast.success('Nœud SQL ajouté au pipeline')
      setAgent(null)
    } catch {
      toast.error("Impossible d'ajouter le nœud")
    }
  }

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Chat "mode action": every message goes through the planning agent.
  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const text = input.trim()
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    setPending(null)
    setAgent(null)
    setIsLoading(true)
    try {
      const plan = await aiService.agentPlan(text, { pipeline_id: pipelineId })
      setMessages((prev) => [...prev, { role: 'assistant', content: plan.message }])
      if (plan.type === 'action') setPending(plan)
    } catch {
      toast.error("Erreur de communication avec l'IA")
    } finally {
      setIsLoading(false)
    }
  }

  const download = (content: string, filename: string, mime: string) => {
    const blob = new Blob([content], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
  }

  // Execute a confirmed action via the existing services.
  const executeAction = async (plan: PlanAction) => {
    const p = plan.params || {}
    switch (plan.action) {
      case 'add_node': {
        const type = String(p.node_type || 'filter')
        const node = await nodeService.addNode(pipelineId, {
          type, label: String(p.label || type), position: { x: 320, y: 320 }, data: { config: {} },
        })
        setNodes([...nodes, { id: node.id, type, position: node.position,
          data: { ...node.data, type_slug: type } } as unknown as import('@xyflow/react').Node])
        toast.success('Nœud ajouté'); break
      }
      case 'run_pipeline': {
        setRunStatus('running')
        const r = await runService.execute(pipelineId)
        setActiveRun(r.run_id); setNodeResults(r.node_results || {})
        Object.entries(r.node_results || {}).forEach(([id, res]) =>
          setNodeStatus(id, res.status === 'error' ? 'error' : 'success'))
        applyLineage(r.node_results || {})
        setRunStatus(r.status === 'success' ? 'success' : 'failed')
        toast.success('Pipeline exécuté'); break
      }
      case 'generate_sql': {
        const result = await aiService.agentTransform(String(p.description || ''), sourceFileId)
        setAgent(result); break   // the agent card handles the apply step
      }
      case 'export_pipeline': {
        const data = await pipelineService.exportPipeline(pipelineId, (p.format === 'json' ? 'json' : 'yaml'))
        const isYaml = typeof data === 'string'
        download(isYaml ? (data as string) : JSON.stringify(data, null, 2),
          `pipeline.${isYaml ? 'yaml' : 'json'}`, isYaml ? 'text/yaml' : 'application/json')
        toast.success('Pipeline exporté'); break
      }
      case 'audit_report': {
        if (!activeRunId) { toast.error("Exécute d'abord le pipeline"); return }
        const report = await runService.getAuditReport(activeRunId)
        download(JSON.stringify(report, null, 2), `rapport_audit.json`, 'application/json')
        toast.success("Rapport d'audit exporté"); break
      }
      default:
        toast.info('Action proposée — à finaliser sur le canvas.')
    }
  }

  const confirmPlan = async () => {
    if (!pending) return
    const plan = pending
    setPending(null)
    setIsLoading(true)
    try {
      await executeAction(plan)
      if (plan.action !== 'generate_sql') {
        setMessages((prev) => [...prev, { role: 'assistant', content: '✅ Action effectuée.' }])
      }
    } catch {
      toast.error("L'action a échoué")
    } finally {
      setIsLoading(false)
    }
  }

  const handleGeneratePipeline = async () => {
    if (!input.trim()) return
    const prompt = input.trim()
    setInput('')
    setIsLoading(true)
    setMessages((prev) => [...prev, { role: 'user', content: `Génère un pipeline : ${prompt}` }])

    try {
      const result = await aiService.generatePipeline(prompt)

      // Build node IDs — cast via unknown to satisfy React Flow's Node type
      const nodesWithIds = result.pipeline.nodes.map((n, i) => ({
        id: `ai_node_${i}`,
        type: String(n.type ?? 'default'),
        position: (n.position as { x: number; y: number }) ?? { x: 100 * i, y: 100 },
        data: { ...(n.data as Record<string, unknown> ?? {}), type_slug: n.type },
      })) as unknown as import('@xyflow/react').Node[]
      const edgesWithIds = result.pipeline.edges.map((e, i) => ({
        id: `ai_edge_${i}`,
        source: String(e.source),
        target: String(e.target),
      }))

      setNodes(nodesWithIds)
      setEdges(edgesWithIds)

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Pipeline généré ! ${result.explanation}\n\n_${result.tokens_used} tokens utilisés_`,
        },
      ])
      toast.success('Pipeline injecté dans le canvas !')
    } catch {
      toast.error('Erreur lors de la génération')
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Désolé, je n\'ai pas pu générer le pipeline.' }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="absolute bottom-4 right-4 z-50 flex h-[520px] w-[380px] flex-col rounded-xl border border-[#d7dbe2] bg-[#eaedf2] shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between rounded-t-xl border-b border-[#e6e8ec] px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-500/20">
            <Sparkles className="h-4 w-4 text-purple-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">Assistant IA</p>
            <p className="text-[10px] text-slate-500">Propulsé par Claude</p>
          </div>
        </div>
        <Button variant="ghost" size="icon-sm" onClick={() => setAIChatOpen(false)}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Quick actions */}
      <div className="flex gap-1.5 border-b border-[#e6e8ec] px-3 py-2">
        <button
          className="flex items-center gap-1 rounded-full border border-[#d7dbe2] bg-[#ffffff] px-2.5 py-1 text-[10px] text-slate-600 hover:border-purple-500/50 hover:text-purple-400 transition-colors"
          onClick={() => setInput('Génère un pipeline pour ')}
        >
          <Zap className="h-2.5 w-2.5" /> Générer pipeline
        </button>
        <button
          className="flex items-center gap-1 rounded-full border border-[#d7dbe2] bg-[#ffffff] px-2.5 py-1 text-[10px] text-slate-600 hover:border-purple-500/50 hover:text-purple-400 transition-colors"
          onClick={() => setInput('Génère du SQL pour ')}
        >
          <Zap className="h-2.5 w-2.5" /> Générer SQL
        </button>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 px-3 py-3">
        <div className="space-y-3">
          {messages.map((msg, i) => (
            <div key={i} className={cn('flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
              <div
                className={cn(
                  'max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed',
                  msg.role === 'user'
                    ? 'bg-[#ff6d35]/20 text-slate-800'
                    : 'bg-[#ffffff] text-slate-700'
                )}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          {/* Proposed action card — user confirms before anything happens */}
          {pending && pending.type === 'action' && (
            <div className="rounded-xl border border-purple-500/30 bg-white p-3 text-xs shadow-sm">
              <div className="mb-1.5 flex items-center gap-1.5 font-semibold text-purple-600">
                <Zap className="h-3.5 w-3.5" /> Action proposée
              </div>
              <p className="mb-1.5 text-slate-700">{pending.message}</p>
              <p className="mb-2 text-[10px] text-slate-500">
                Action : <code className="rounded bg-slate-100 px-1">{pending.action}</code>
              </p>
              {pending.warning && (
                <div className="mb-2 flex items-start gap-1 text-amber-600">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {pending.warning}
                </div>
              )}
              <div className="flex gap-2">
                <Button size="sm" className="flex-1 gap-1.5" onClick={confirmPlan}>
                  {pending.action === 'run_pipeline'
                    ? <><Play className="h-3.5 w-3.5" /> Confirmer</>
                    : <><Check className="h-3.5 w-3.5" /> Confirmer</>}
                </Button>
                <Button size="sm" variant="outline" className="flex-1" onClick={() => setPending(null)}>
                  Annuler
                </Button>
              </div>
            </div>
          )}

          {/* Controlled-agent card: SQL + explanation + dry-run preview + validation */}
          {agent && (
            <div className="rounded-xl border border-purple-500/30 bg-white p-3 text-xs shadow-sm">
              <div className="mb-2 flex items-center gap-1.5 font-semibold text-purple-600">
                <Sparkles className="h-3.5 w-3.5" /> Proposition de l&apos;agent
              </div>
              <p className="mb-2 text-slate-600">{agent.explanation}</p>
              <pre className="mb-2 overflow-auto rounded-lg bg-slate-900 p-2 text-[10px] leading-relaxed text-emerald-300">
                {agent.generated_sql}
              </pre>

              {agent.validation.safe ? (
                <div className="mb-2 flex items-center gap-1 text-emerald-600">
                  <ShieldCheck className="h-3.5 w-3.5" /> Requête sûre (lecture seule)
                </div>
              ) : (
                <div className="mb-2 flex items-center gap-1 text-red-500">
                  <AlertTriangle className="h-3.5 w-3.5" /> {agent.validation.issues.join(' · ')}
                </div>
              )}

              {agent.sample && agent.sample.rows_in > 0 && (
                <div className="mb-2 rounded-lg bg-slate-50 p-2 text-[10px] text-slate-600">
                  <p className="font-medium text-slate-700">Test sur échantillon réel :</p>
                  <p>{agent.sample.rows_in} → {agent.sample.rows_out} lignes
                    {agent.sample.quality_after &&
                      ` · qualité ${agent.sample.quality_after.score}%`}</p>
                </div>
              )}

              <Button size="sm" className="w-full gap-1.5" disabled={!agent.validation.safe}
                      onClick={applyAgent}>
                <Check className="h-3.5 w-3.5" /> Appliquer comme nœud SQL
              </Button>
            </div>
          )}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-[#ffffff] rounded-xl px-3 py-2">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-purple-400" />
              </div>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-[#e6e8ec] p-3 space-y-2">
        <Textarea
          className="min-h-[60px] resize-none text-xs"
          placeholder="Posez votre question ou décrivez le pipeline à créer…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="flex items-center justify-between gap-1">
          <div className="flex items-center gap-1">
            <Button
              variant="ghost" size="sm"
              className="text-xs text-purple-500 hover:text-purple-600 gap-1.5"
              onClick={handleGeneratePipeline}
              disabled={!input.trim() || isLoading}
            >
              <Sparkles className="h-3.5 w-3.5" /> Pipeline
            </Button>
            <Button
              variant="ghost" size="sm"
              className="text-xs text-purple-500 hover:text-purple-600 gap-1.5"
              onClick={handleAgent}
              disabled={!input.trim() || isLoading}
              title="Génère du SQL, le teste sur un échantillon réel, puis tu valides"
            >
              <ShieldCheck className="h-3.5 w-3.5" /> Agent SQL
            </Button>
          </div>
          <Button size="sm" onClick={handleSend} disabled={!input.trim() || isLoading}>
            <Send className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  )
}
