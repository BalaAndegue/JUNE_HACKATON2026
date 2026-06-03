'use client'

import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import type { SQLQueryConfig } from '@/types/nodeConfigs'

interface Props {
  config: SQLQueryConfig
  onChange: (cfg: SQLQueryConfig) => void
}

export function InspectorSQLQuery({ config, onChange }: Props) {
  const update = (patch: Partial<SQLQueryConfig>) => onChange({ ...config, ...patch })

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>Type de connexion</Label>
        <Select
          value={config.connection ?? 'sqlite'}
          onValueChange={(v) => update({ connection: v as SQLQueryConfig['connection'] })}
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="sqlite">SQLite (fichier local)</SelectItem>
            <SelectItem value="postgres">PostgreSQL</SelectItem>
            <SelectItem value="mysql">MySQL / MariaDB</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {config.connection !== 'sqlite' && (
        <div className="space-y-1.5">
          <Label>Chaîne de connexion</Label>
          <Input
            type="password"
            placeholder="postgresql://user:pass@host:5432/db"
            value={config.connection_string ?? ''}
            onChange={(e) => update({ connection_string: e.target.value })}
          />
        </div>
      )}

      <div className="space-y-1.5">
        <Label>Requête SQL</Label>
        <Textarea
          className="font-mono text-xs min-h-[140px] resize-none"
          placeholder={'SELECT *\nFROM table\nWHERE condition\nLIMIT 1000'}
          value={config.query ?? ''}
          onChange={(e) => update({ query: e.target.value })}
          spellCheck={false}
        />
        <p className="text-[10px] text-gray-600">
          Astuce : utilisez LIMIT pour éviter de charger trop de données
        </p>
      </div>
    </div>
  )
}
