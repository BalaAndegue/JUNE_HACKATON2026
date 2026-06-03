'use client'

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { JoinConfig } from '@/types/nodeConfigs'

interface Props {
  config: JoinConfig
  leftColumns: string[]
  rightColumns: string[]
  onChange: (cfg: JoinConfig) => void
}

export function InspectorJoin({ config, leftColumns, rightColumns, onChange }: Props) {
  const update = (patch: Partial<JoinConfig>) => onChange({ ...config, ...patch })

  const ColPicker = ({ label, value, cols, onPick }: {
    label: string; value?: string; cols: string[]; onPick: (v: string) => void
  }) => (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {cols.length > 0 ? (
        <Select value={value ?? ''} onValueChange={onPick}>
          <SelectTrigger><SelectValue placeholder="Choisir…" /></SelectTrigger>
          <SelectContent>{cols.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
        </Select>
      ) : (
        <Input placeholder="nom_colonne" value={value ?? ''} onChange={(e) => onPick(e.target.value)} />
      )}
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>Type de jointure <span className="text-[#ff6d35]">*</span></Label>
        <Select value={config.join_type ?? 'LEFT'} onValueChange={(v) => update({ join_type: v as JoinConfig['join_type'] })}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="LEFT">LEFT JOIN — garder toutes les lignes gauches</SelectItem>
            <SelectItem value="INNER">INNER JOIN — seulement les matches</SelectItem>
            <SelectItem value="RIGHT">RIGHT JOIN — garder toutes les lignes droites</SelectItem>
            <SelectItem value="OUTER">FULL OUTER JOIN — toutes les lignes</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border border-[#e6e8ec] bg-[#eaedf2] p-3 space-y-3">
        <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wide">Clés de jointure</p>
        <ColPicker
          label="Clé gauche (flux du haut)"
          value={config.left_key}
          cols={leftColumns}
          onPick={(v) => update({ left_key: v })}
        />
        <ColPicker
          label="Clé droite (flux du bas)"
          value={config.right_key}
          cols={rightColumns}
          onPick={(v) => update({ right_key: v })}
        />
      </div>

      {config.left_key && config.right_key && (
        <div className="rounded-lg bg-blue-500/10 border border-blue-500/20 px-3 py-2">
          <p className="text-[10px] font-mono text-blue-400">
            {config.join_type ?? 'LEFT'} JOIN ON left.{config.left_key} = right.{config.right_key}
          </p>
        </div>
      )}
    </div>
  )
}
