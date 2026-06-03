'use client'

import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { FileText, Upload } from 'lucide-react'
import type { CSVImportConfig } from '@/types/nodeConfigs'

interface Props {
  config: CSVImportConfig
  files: Array<{ id: string; name: string; rows?: number; columns?: number }>
  onChange: (cfg: CSVImportConfig) => void
}

export function InspectorCSVImport({ config, files, onChange }: Props) {
  const update = (patch: Partial<CSVImportConfig>) => onChange({ ...config, ...patch })
  const selectedFile = files.find(f => f.id === config.file_id)

  return (
    <div className="space-y-4">
      {/* File picker */}
      <div className="space-y-1.5">
        <Label>Fichier CSV</Label>
        <Select value={config.file_id ?? ''} onValueChange={(v) => {
          const f = files.find(f => f.id === v)
          update({ file_id: v, file_name: f?.name })
        }}>
          <SelectTrigger>
            <SelectValue placeholder="Sélectionner un fichier…" />
          </SelectTrigger>
          <SelectContent>
            {files.length === 0 && (
              <div className="px-3 py-2 text-xs text-slate-500">
                Aucun fichier CSV uploadé
              </div>
            )}
            {files.map(f => (
              <SelectItem key={f.id} value={f.id}>
                <div className="flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-emerald-400" />
                  <span>{f.name}</span>
                  {f.rows && <span className="text-slate-500 text-xs">({f.rows} lignes)</span>}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* File info badge */}
      {selectedFile && (
        <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 space-y-1">
          <p className="text-xs text-emerald-400 font-medium">{selectedFile.name}</p>
          <div className="flex gap-3 text-[10px] text-slate-500">
            {selectedFile.rows && <span>{selectedFile.rows} lignes</span>}
            {selectedFile.columns && <span>{selectedFile.columns} colonnes</span>}
          </div>
        </div>
      )}

      {/* Separator */}
      <div className="space-y-1.5">
        <Label>Séparateur</Label>
        <Select value={config.separator ?? ','} onValueChange={(v) => update({ separator: v as CSVImportConfig['separator'] })}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value=",">Virgule (,)</SelectItem>
            <SelectItem value=";">Point-virgule (;)</SelectItem>
            <SelectItem value={'\t'}>Tabulation</SelectItem>
            <SelectItem value="|">Pipe (|)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Encoding */}
      <div className="space-y-1.5">
        <Label>Encodage</Label>
        <Select value={config.encoding ?? 'utf-8'} onValueChange={(v) => update({ encoding: v as CSVImportConfig['encoding'] })}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="utf-8">UTF-8</SelectItem>
            <SelectItem value="latin-1">Latin-1 (ISO-8859-1)</SelectItem>
            <SelectItem value="utf-16">UTF-16</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <Label>Ligne d'en-tête</Label>
          <p className="text-[10px] text-slate-500">La 1ère ligne contient les noms de colonnes</p>
        </div>
        <Switch
          checked={config.has_header !== false}
          onCheckedChange={(v) => update({ has_header: v })}
        />
      </div>
    </div>
  )
}
