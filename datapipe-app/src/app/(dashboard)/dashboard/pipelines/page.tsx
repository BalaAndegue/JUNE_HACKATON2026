'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Search, GitBranch, MoreHorizontal, Zap, Archive, Copy, Trash2, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { pipelineService } from '@/services/pipeline.service'
import { getRelativeTime } from '@/lib/utils'
import { toast } from 'sonner'
import { useAuthStore } from '@/store/auth.store'
import type { Pipeline } from '@/types'

export default function PipelinesPage() {
  const router = useRouter()
  const { isDemoMode } = useAuthStore()
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [search, setSearch] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    loadPipelines()
  }, [search])

  const DEMO_PIPELINES: Pipeline[] = [
    { id: 'demo-sales', name: 'Analyse des ventes 2024', description: 'CSV → Filtre → Agrégation → Chart', status: 'active', nodes_count: 4, last_run_status: 'success', last_run_at: new Date(Date.now() - 3600000).toISOString(), workspace_id: 'demo', created_at: '', updated_at: '' },
    { id: 'demo-crm',   name: 'Nettoyage CRM clients',  description: 'JSON → Nettoyage → Rename → Export', status: 'active', nodes_count: 4, last_run_status: 'success', last_run_at: new Date(Date.now() - 7200000).toISOString(), workspace_id: 'demo', created_at: '', updated_at: '' },
    { id: 'demo-ai',    name: 'IA Transform — revenus',  description: 'CSV → IA Transform → Table Preview', status: 'active', nodes_count: 3, last_run_status: 'failed',  last_run_at: new Date(Date.now() - 900000).toISOString(),  workspace_id: 'demo', created_at: '', updated_at: '' },
  ]

  const loadPipelines = async () => {
    if (isDemoMode) {
      setIsLoading(false)
      setPipelines(DEMO_PIPELINES)
      return
    }
    setIsLoading(true)
    try {
      const res = await pipelineService.list({ workspace_id: 'default', search, per_page: 50 })
      setPipelines(res.data)
    } catch {
      toast.error('Erreur de chargement')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setIsCreating(true)
    try {
      const p = await pipelineService.create({ name: newName, workspace_id: 'default' })
      toast.success('Pipeline créé')
      setShowCreate(false)
      setNewName('')
      router.push(`/dashboard/pipelines/${p.id}/editor`)
    } catch {
      if (isDemoMode) {
        toast.info('Mode démo — connexion API requise pour créer un pipeline')
        setShowCreate(false)
      } else {
        toast.error('Erreur lors de la création')
      }
    } finally {
      setIsCreating(false)
    }
  }

  const handleDuplicate = async (p: Pipeline) => {
    try {
      await pipelineService.duplicate(p.id)
      toast.success('Pipeline dupliqué')
      loadPipelines()
    } catch { toast.error('Erreur') }
  }

  const handleDelete = async (p: Pipeline) => {
    try {
      await pipelineService.delete(p.id)
      toast.success('Pipeline supprimé')
      loadPipelines()
    } catch { toast.error('Erreur') }
  }

  const statusVariant = (status?: string) => {
    if (status === 'success') return 'success'
    if (status === 'failed') return 'destructive'
    if (status === 'running') return 'running'
    return 'secondary'
  }

  return (
    <div className="p-6 space-y-5 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Pipelines</h1>
          <p className="text-sm text-slate-500">{pipelines.length} pipeline{pipelines.length > 1 ? 's' : ''}</p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2">
          <Plus className="h-4 w-4" /> Nouveau pipeline
        </Button>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <Input
          className="pl-9"
          placeholder="Rechercher un pipeline…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-36" />)}
        </div>
      ) : pipelines.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[#d7dbe2] py-16 gap-4">
          <GitBranch className="h-12 w-12 text-gray-700" />
          <div className="text-center">
            <p className="text-slate-600 font-medium">Aucun pipeline</p>
            <p className="text-sm text-slate-500 mt-1">
              {isDemoMode ? 'Connectez une API pour voir vos pipelines' : 'Créez votre premier pipeline pour commencer'}
            </p>
          </div>
          <Button onClick={() => setShowCreate(true)} className="gap-2">
            <Plus className="h-4 w-4" /> Créer un pipeline
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {pipelines.map((p) => (
            <Card
              key={p.id}
              className="group relative cursor-pointer transition-all hover:border-[#d7dbe2] hover:shadow-lg hover:shadow-black/20"
              onClick={() => router.push(`/dashboard/pipelines/${p.id}/editor`)}
            >
              <div className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#ff6d35]/10">
                      <Zap className="h-4 w-4 text-[#ff6d35]" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-800 group-hover:text-slate-900 transition-colors">{p.name}</p>
                      <p className="text-xs text-slate-500">{p.nodes_count ?? 0} nœuds</p>
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="icon-sm" className="opacity-0 group-hover:opacity-100">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                      <DropdownMenuItem onClick={() => router.push(`/dashboard/pipelines/${p.id}/editor`)}>
                        <ExternalLink className="h-4 w-4" /> Ouvrir
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleDuplicate(p)}>
                        <Copy className="h-4 w-4" /> Dupliquer
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => handleDelete(p)} className="text-red-400 focus:text-red-400">
                        <Trash2 className="h-4 w-4" /> Supprimer
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                {p.description && (
                  <p className="text-xs text-slate-500 line-clamp-2">{p.description}</p>
                )}

                <div className="flex items-center justify-between pt-1 border-t border-[#e6e8ec]">
                  <Badge variant={statusVariant(p.last_run_status)} className="text-[10px] h-5">
                    {p.last_run_status ?? 'jamais exécuté'}
                  </Badge>
                  <p className="text-[10px] text-gray-700">
                    {p.last_run_at ? getRelativeTime(p.last_run_at) : '—'}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouveau pipeline</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1.5">
              <Label>Nom du pipeline</Label>
              <Input
                placeholder="Ex: Réconciliation bancaire mensuelle"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                autoFocus
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Annuler</Button>
            <Button onClick={handleCreate} disabled={isCreating || !newName.trim()}>
              {isCreating ? 'Création…' : 'Créer et ouvrir'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
