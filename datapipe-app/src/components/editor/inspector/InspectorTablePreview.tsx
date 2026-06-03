'use client'

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { TablePreviewConfig } from '@/types/nodeConfigs'

interface Props {
  config: TablePreviewConfig
  columns: string[]
  onChange: (cfg: TablePreviewConfig) => void
}

export function InspectorTablePreview({ config, columns, onChange }: Props) {
  const update = (patch: Partial<TablePreviewConfig>) => onChange({ ...config, ...patch })

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>Lignes par page</Label>
        <Select
          value={String(config.page_size ?? 25)}
          onValueChange={(v) => update({ page_size: Number(v) })}
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {[10, 25, 50, 100].map(n => <SelectItem key={n} value={String(n)}>{n} lignes</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>Tri par défaut</Label>
        {columns.length > 0 ? (
          <Select value={config.sort_column ?? ''} onValueChange={(v) => update({ sort_column: v || undefined })}>
            <SelectTrigger><SelectValue placeholder="Aucun tri" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="">Aucun tri</SelectItem>
              {columns.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
            </SelectContent>
          </Select>
        ) : (
          <Input
            placeholder="nom_colonne"
            value={config.sort_column ?? ''}
            onChange={(e) => update({ sort_column: e.target.value || undefined })}
          />
        )}
      </div>

      {config.sort_column && (
        <div className="space-y-1.5">
          <Label>Direction</Label>
          <Select value={config.sort_dir ?? 'asc'} onValueChange={(v) => update({ sort_dir: v as 'asc' | 'desc' })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="asc">Croissant ↑</SelectItem>
              <SelectItem value="desc">Décroissant ↓</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 px-3 py-2">
        <p className="text-[10px] text-amber-400">
          Le tableau apparaît dans l'onglet &quot;Données&quot; de la console après exécution
        </p>
      </div>
    </div>
  )
}
