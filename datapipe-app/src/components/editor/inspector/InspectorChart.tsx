'use client'

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import type { ChartConfig } from '@/types/nodeConfigs'

const CHART_TYPES = [
  { value: 'bar', label: '📊 Barres', desc: 'Comparaison de catégories' },
  { value: 'line', label: '📈 Ligne', desc: 'Évolution dans le temps' },
  { value: 'pie', label: '🥧 Camembert', desc: 'Répartition en parts' },
  { value: 'area', label: '🏔️ Aires', desc: 'Volumes cumulés' },
]

const COLORS = [
  '#ff6d35', '#3b82f6', '#a855f7', '#00e5a0', '#f59e0b', '#ef4444',
]

interface Props {
  config: ChartConfig
  columns: string[]
  onChange: (cfg: ChartConfig) => void
}

export function InspectorChart({ config, columns, onChange }: Props) {
  const update = (patch: Partial<ChartConfig>) => onChange({ ...config, ...patch })

  return (
    <div className="space-y-4">
      {/* Chart type */}
      <div className="space-y-1.5">
        <Label>Type de graphique <span className="text-[#ff6d35]">*</span></Label>
        <div className="grid grid-cols-2 gap-1.5">
          {CHART_TYPES.map(ct => (
            <button
              key={ct.value}
              onClick={() => update({ chart_type: ct.value as ChartConfig['chart_type'] })}
              className={`rounded-lg border px-2.5 py-2 text-left text-xs transition-colors ${
                config.chart_type === ct.value
                  ? 'border-[#ff6d35] bg-[#ff6d35]/10 text-[#ff6d35]'
                  : 'border-[#d7dbe2] text-slate-500 hover:border-[#c3c9d2] hover:text-slate-700'
              }`}
            >
              <p className="font-medium">{ct.label}</p>
              <p className="text-[9px] mt-0.5 opacity-60">{ct.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Axes */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label>Axe X <span className="text-[#ff6d35]">*</span></Label>
          {columns.length > 0 ? (
            <Select value={config.x_axis ?? ''} onValueChange={(v) => update({ x_axis: v })}>
              <SelectTrigger><SelectValue placeholder="Colonne…" /></SelectTrigger>
              <SelectContent>{columns.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
          ) : (
            <Input placeholder="colonne_x" value={config.x_axis ?? ''} onChange={(e) => update({ x_axis: e.target.value })} />
          )}
        </div>

        {config.chart_type !== 'pie' && (
          <div className="space-y-1.5">
            <Label>Axe Y <span className="text-[#ff6d35]">*</span></Label>
            {columns.length > 0 ? (
              <Select value={config.y_axis ?? ''} onValueChange={(v) => update({ y_axis: v })}>
                <SelectTrigger><SelectValue placeholder="Colonne…" /></SelectTrigger>
                <SelectContent>{columns.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            ) : (
              <Input placeholder="colonne_y" value={config.y_axis ?? ''} onChange={(e) => update({ y_axis: e.target.value })} />
            )}
          </div>
        )}
      </div>

      {/* Title */}
      <div className="space-y-1.5">
        <Label>Titre <span className="text-slate-500">(optionnel)</span></Label>
        <Input
          placeholder="Mon graphique"
          value={config.title ?? ''}
          onChange={(e) => update({ title: e.target.value || undefined })}
        />
      </div>

      {/* Color */}
      <div className="space-y-1.5">
        <Label>Couleur principale</Label>
        <div className="flex gap-2">
          {COLORS.map(c => (
            <button
              key={c}
              className={`h-7 w-7 rounded-full transition-all ${config.color === c ? 'ring-2 ring-white ring-offset-2 ring-offset-[#f4f6f9]' : ''}`}
              style={{ background: c }}
              onClick={() => update({ color: c })}
            />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between">
        <Label>Afficher la légende</Label>
        <Switch
          checked={config.show_legend ?? true}
          onCheckedChange={(v) => update({ show_legend: v })}
        />
      </div>
    </div>
  )
}
