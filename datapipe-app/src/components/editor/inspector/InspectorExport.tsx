'use client'

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import type { ExportConfig } from '@/types/nodeConfigs'

interface Props {
  config: ExportConfig
  onChange: (cfg: ExportConfig) => void
}

export function InspectorExport({ config, onChange }: Props) {
  const update = (patch: Partial<ExportConfig>) => onChange({ ...config, ...patch })

  return (
    <div className="space-y-4">
      {/* Format */}
      <div className="space-y-1.5">
        <Label>Format de sortie <span className="text-[#ff6d35]">*</span></Label>
        <div className="grid grid-cols-2 gap-2">
          {(['csv', 'json'] as const).map(fmt => (
            <button
              key={fmt}
              onClick={() => update({ format: fmt })}
              className={`rounded-lg border py-3 text-center font-mono text-sm font-bold uppercase transition-colors ${
                config.format === fmt
                  ? 'border-[#ff6d35] bg-[#ff6d35]/10 text-[#ff6d35]'
                  : 'border-[#2a2a2a] text-gray-500 hover:border-[#3a3a3a] hover:text-gray-300'
              }`}
            >
              {fmt}
            </button>
          ))}
        </div>
      </div>

      {/* Filename */}
      <div className="space-y-1.5">
        <Label>Nom du fichier <span className="text-gray-600">(optionnel)</span></Label>
        <div className="flex items-center gap-1">
          <Input
            placeholder="export"
            value={config.filename ?? ''}
            onChange={(e) => update({ filename: e.target.value || undefined })}
          />
          <span className="text-xs text-gray-600 shrink-0">.{config.format ?? 'csv'}</span>
        </div>
      </div>

      {/* Include index */}
      {config.format === 'csv' && (
        <div className="flex items-center justify-between">
          <div>
            <Label>Inclure l'index</Label>
            <p className="text-[10px] text-gray-600">Ajoute une colonne numéro de ligne</p>
          </div>
          <Switch
            checked={config.include_index ?? false}
            onCheckedChange={(v) => update({ include_index: v })}
          />
        </div>
      )}

      {config.format && (
        <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 px-3 py-2">
          <p className="text-[10px] text-amber-400">
            Après exécution, un bouton de téléchargement apparaîtra dans la console.
          </p>
        </div>
      )}
    </div>
  )
}
