'use client'

import { useState } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Plus, X } from 'lucide-react'
import type { AggregateConfig } from '@/types/nodeConfigs'

const AGG_FUNCTIONS = ['SUM', 'COUNT', 'AVG', 'MAX', 'MIN', 'FIRST', 'LAST']

interface Props {
  config: AggregateConfig
  columns: string[]
  onChange: (cfg: AggregateConfig) => void
}

export function InspectorAggregate({ config, columns, onChange }: Props) {
  const update = (patch: Partial<AggregateConfig>) => onChange({ ...config, ...patch })
  const [newGroupCol, setNewGroupCol] = useState('')
  const [newAggCol, setNewAggCol] = useState('')
  const [newAggFn, setNewAggFn] = useState('SUM')

  const groupBy = config.group_by ?? []
  const aggs = config.aggregations ?? []

  const addGroup = (col: string) => {
    if (!col || groupBy.includes(col)) return
    update({ group_by: [...groupBy, col] })
    setNewGroupCol('')
  }

  const removeGroup = (col: string) => update({ group_by: groupBy.filter(c => c !== col) })

  const addAgg = () => {
    if (!newAggCol) return
    update({
      aggregations: [...aggs, { column: newAggCol, function: newAggFn as 'SUM' | 'COUNT' | 'AVG' | 'MAX' | 'MIN' }]
    })
    setNewAggCol('')
  }

  const removeAgg = (i: number) => update({ aggregations: aggs.filter((_, idx) => idx !== i) })

  return (
    <div className="space-y-5">
      {/* GROUP BY */}
      <div className="space-y-2">
        <Label>GROUP BY</Label>
        <div className="flex gap-2">
          {columns.length > 0 ? (
            <Select value="" onValueChange={(v) => addGroup(v)}>
              <SelectTrigger className="flex-1"><SelectValue placeholder="Ajouter une colonne…" /></SelectTrigger>
              <SelectContent>{columns.filter(c => !groupBy.includes(c)).map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
          ) : (
            <>
              <Input className="flex-1" placeholder="nom_colonne" value={newGroupCol} onChange={(e) => setNewGroupCol(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addGroup(newGroupCol)} />
              <Button size="icon-sm" variant="outline" onClick={() => addGroup(newGroupCol)}><Plus className="h-3.5 w-3.5" /></Button>
            </>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5 min-h-[24px]">
          {groupBy.map(c => (
            <Badge key={c} variant="secondary" className="gap-1">
              {c}
              <button onClick={() => removeGroup(c)}><X className="h-2.5 w-2.5" /></button>
            </Badge>
          ))}
          {groupBy.length === 0 && <p className="text-[10px] text-gray-700">Aucune colonne GROUP BY</p>}
        </div>
      </div>

      {/* Aggregations */}
      <div className="space-y-2">
        <Label>Agrégations</Label>
        <div className="flex gap-2">
          {columns.length > 0 ? (
            <Select value={newAggCol} onValueChange={setNewAggCol}>
              <SelectTrigger className="flex-1"><SelectValue placeholder="Colonne…" /></SelectTrigger>
              <SelectContent>{columns.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
          ) : (
            <Input className="flex-1" placeholder="colonne" value={newAggCol} onChange={(e) => setNewAggCol(e.target.value)} />
          )}
          <Select value={newAggFn} onValueChange={setNewAggFn}>
            <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
            <SelectContent>{AGG_FUNCTIONS.map(f => <SelectItem key={f} value={f}>{f}</SelectItem>)}</SelectContent>
          </Select>
          <Button size="icon-sm" variant="outline" onClick={addAgg}><Plus className="h-3.5 w-3.5" /></Button>
        </div>
        <div className="space-y-1">
          {aggs.map((a, i) => (
            <div key={i} className="flex items-center justify-between rounded bg-[#ffffff] px-2.5 py-1.5">
              <span className="font-mono text-[10px] text-blue-400">{a.function}({a.column})</span>
              <button onClick={() => removeAgg(i)}><X className="h-3 w-3 text-slate-500 hover:text-red-400" /></button>
            </div>
          ))}
          {aggs.length === 0 && <p className="text-[10px] text-gray-700">Aucune agrégation définie</p>}
        </div>
      </div>
    </div>
  )
}
