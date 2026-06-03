'use client'

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import type { CleanConfig } from '@/types/nodeConfigs'

interface Props {
  config: CleanConfig
  onChange: (cfg: CleanConfig) => void
}

export function InspectorClean({ config, onChange }: Props) {
  const update = (patch: Partial<CleanConfig>) => onChange({ ...config, ...patch })

  const Row = ({ label, desc, checked, onToggle }: {
    label: string; desc: string; checked: boolean; onToggle: (v: boolean) => void
  }) => (
    <div className="flex items-center justify-between py-2.5 border-b border-[#f1f3f6]">
      <div>
        <p className="text-sm text-slate-700">{label}</p>
        <p className="text-[10px] text-slate-500">{desc}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onToggle} />
    </div>
  )

  return (
    <div className="space-y-1">
      <Row
        label="Supprimer les doublons"
        desc="Élimine les lignes identiques"
        checked={config.remove_duplicates ?? false}
        onToggle={(v) => update({ remove_duplicates: v })}
      />
      <Row
        label="Supprimer les lignes nulles"
        desc="Retire toute ligne avec au moins une valeur nulle"
        checked={config.drop_null_rows ?? false}
        onToggle={(v) => update({ drop_null_rows: v })}
      />
      <Row
        label="Supprimer les colonnes vides"
        desc="Retire les colonnes 100% nulles"
        checked={config.drop_columns_all_null ?? false}
        onToggle={(v) => update({ drop_columns_all_null: v })}
      />
      <Row
        label="Trim les chaînes"
        desc="Supprime les espaces en début/fin"
        checked={config.trim_strings ?? false}
        onToggle={(v) => update({ trim_strings: v })}
      />

      {/* Null fill value */}
      <div className="pt-3 space-y-1.5">
        <Label>Remplacer les nulls par</Label>
        <Input
          placeholder="ex: 0, N/A, inconnu…"
          value={config.fill_null_value ?? ''}
          onChange={(e) => update({ fill_null_value: e.target.value })}
        />
        <p className="text-[10px] text-slate-500">Vide = ne pas remplacer</p>
      </div>
    </div>
  )
}
