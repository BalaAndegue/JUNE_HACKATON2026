'use client'

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { FilterConfig } from '@/types/nodeConfigs'

const OPERATORS = [
  { value: '==', label: '= égal' },
  { value: '!=', label: '≠ différent' },
  { value: '>', label: '> supérieur' },
  { value: '>=', label: '≥ supérieur ou égal' },
  { value: '<', label: '< inférieur' },
  { value: '<=', label: '≤ inférieur ou égal' },
  { value: 'contains', label: '∋ contient' },
  { value: 'not contains', label: '∌ ne contient pas' },
  { value: 'is null', label: '∅ est null' },
  { value: 'is not null', label: '✓ n\'est pas null' },
]

const NO_VALUE_OPS = ['is null', 'is not null']

interface Props {
  config: FilterConfig
  columns: string[]
  onChange: (cfg: FilterConfig) => void
}

export function InspectorFilter({ config, columns, onChange }: Props) {
  const update = (patch: Partial<FilterConfig>) => onChange({ ...config, ...patch })
  const showValue = !NO_VALUE_OPS.includes(config.operator ?? '')

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>Colonne <span className="text-[#ff6d35]">*</span></Label>
        {columns.length > 0 ? (
          <Select value={config.column ?? ''} onValueChange={(v) => update({ column: v })}>
            <SelectTrigger><SelectValue placeholder="Choisir une colonne…" /></SelectTrigger>
            <SelectContent>
              {columns.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
            </SelectContent>
          </Select>
        ) : (
          <Input
            placeholder="nom_colonne"
            value={config.column ?? ''}
            onChange={(e) => update({ column: e.target.value })}
          />
        )}
      </div>

      <div className="space-y-1.5">
        <Label>Condition <span className="text-[#ff6d35]">*</span></Label>
        <Select
          value={config.operator ?? '=='}
          onValueChange={(v) => update({ operator: v as FilterConfig['operator'] })}
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {OPERATORS.map(op => (
              <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {showValue && (
        <div className="space-y-1.5">
          <Label>Valeur <span className="text-[#ff6d35]">*</span></Label>
          <Input
            placeholder="valeur à comparer"
            value={config.value ?? ''}
            onChange={(e) => update({ value: e.target.value })}
          />
          <p className="text-[10px] text-gray-600">Pour les nombres, entrez uniquement le chiffre (ex: 42)</p>
        </div>
      )}

      {/* Live preview */}
      {config.column && config.operator && (
        <div className="rounded-lg bg-blue-500/10 border border-blue-500/20 px-3 py-2">
          <p className="text-[10px] font-mono text-blue-400">
            df[df[&quot;{config.column}&quot;] {config.operator} {showValue ? `&quot;${config.value ?? '…'}&quot;` : ''}]
          </p>
        </div>
      )}
    </div>
  )
}
