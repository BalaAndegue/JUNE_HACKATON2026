'use client'

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { JSONLoaderConfig } from '@/types/nodeConfigs'

interface Props {
  config: JSONLoaderConfig
  files: Array<{ id: string; name: string }>
  onChange: (cfg: JSONLoaderConfig) => void
}

export function InspectorJSONLoader({ config, files, onChange }: Props) {
  const update = (patch: Partial<JSONLoaderConfig>) => onChange({ ...config, ...patch })
  const source = config.source ?? 'file'

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>Source</Label>
        <Tabs value={source} onValueChange={(v) => update({ source: v as 'file' | 'url' })}>
          <TabsList className="w-full">
            <TabsTrigger value="file" className="flex-1">Fichier</TabsTrigger>
            <TabsTrigger value="url" className="flex-1">URL / API</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {source === 'file' ? (
        <div className="space-y-1.5">
          <Label>Fichier JSON</Label>
          <Select value={config.file_id ?? ''} onValueChange={(v) => {
            const f = files.find(f => f.id === v)
            update({ file_id: v, file_name: f?.name })
          }}>
            <SelectTrigger>
              <SelectValue placeholder="Sélectionner un fichier…" />
            </SelectTrigger>
            <SelectContent>
              {files.map(f => (
                <SelectItem key={f.id} value={f.id}>{f.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      ) : (
        <div className="space-y-1.5">
          <Label>URL de l'API</Label>
          <Input
            placeholder="https://api.exemple.com/data"
            value={config.url ?? ''}
            onChange={(e) => update({ url: e.target.value })}
          />
          <p className="text-[10px] text-slate-500">Supporte GET avec réponse JSON</p>
        </div>
      )}

      <div className="space-y-1.5">
        <Label>Chemin de la clé racine <span className="text-slate-500">(optionnel)</span></Label>
        <Input
          placeholder="ex: data.items"
          value={config.root_path ?? ''}
          onChange={(e) => update({ root_path: e.target.value })}
        />
        <p className="text-[10px] text-slate-500">
          Chemin pointé vers le tableau de données. Vide = racine.
        </p>
      </div>
    </div>
  )
}
