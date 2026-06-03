'use client'

import { useState } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Plus, X, ArrowRight, Trash2 } from 'lucide-react'
import type { RenameConfig } from '@/types/nodeConfigs'

interface Props {
  config: RenameConfig
  columns: string[]
  onChange: (cfg: RenameConfig) => void
}

export function InspectorRename({ config, columns, onChange }: Props) {
  const ops = config.operations ?? []
  const update = (operations: RenameConfig['operations']) => onChange({ ...config, operations })

  const [fromCol, setFromCol] = useState('')
  const [toCol, setToCol] = useState('')
  const [dropCol, setDropCol] = useState('')

  const addRename = () => {
    if (!fromCol || !toCol) return
    update([...ops, { op: 'rename', from: fromCol, to: toCol }])
    setFromCol('')
    setToCol('')
  }

  const addDrop = (col: string) => {
    if (!col) return
    update([...ops, { op: 'drop', column: col }])
    setDropCol('')
  }

  const remove = (i: number) => update(ops.filter((_, idx) => idx !== i))

  return (
    <div className="space-y-5">
      {/* Rename */}
      <div className="space-y-2">
        <Label>Renommer une colonne</Label>
        <div className="flex items-center gap-2">
          {columns.length > 0 ? (
            <Select value={fromCol} onValueChange={setFromCol}>
              <SelectTrigger className="flex-1"><SelectValue placeholder="De…" /></SelectTrigger>
              <SelectContent>{columns.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
          ) : (
            <Input className="flex-1" placeholder="ancienne_col" value={fromCol} onChange={(e) => setFromCol(e.target.value)} />
          )}
          <ArrowRight className="h-3.5 w-3.5 text-slate-500 shrink-0" />
          <Input className="flex-1" placeholder="nouvelle_col" value={toCol} onChange={(e) => setToCol(e.target.value)} />
          <Button size="icon-sm" variant="outline" onClick={addRename}><Plus className="h-3.5 w-3.5" /></Button>
        </div>
      </div>

      {/* Drop */}
      <div className="space-y-2">
        <Label>Supprimer une colonne</Label>
        <div className="flex gap-2">
          {columns.length > 0 ? (
            <Select value="" onValueChange={(v) => addDrop(v)}>
              <SelectTrigger className="flex-1"><SelectValue placeholder="Colonne à supprimer…" /></SelectTrigger>
              <SelectContent>{columns.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
          ) : (
            <>
              <Input className="flex-1" placeholder="colonne" value={dropCol} onChange={(e) => setDropCol(e.target.value)} />
              <Button size="icon-sm" variant="outline" onClick={() => addDrop(dropCol)}><Trash2 className="h-3.5 w-3.5" /></Button>
            </>
          )}
        </div>
      </div>

      {/* Op list */}
      <div className="space-y-1.5">
        <Label className="text-[10px] uppercase tracking-widest text-gray-700">Opérations ({ops.length})</Label>
        {ops.length === 0 ? (
          <p className="text-[10px] text-gray-700">Aucune opération définie</p>
        ) : (
          ops.map((op, i) => (
            <div key={i} className="flex items-center justify-between rounded bg-[#ffffff] px-2.5 py-1.5">
              {'from' in op ? (
                <span className="font-mono text-[10px] text-blue-400">
                  rename: {op.from} → {op.to}
                </span>
              ) : 'column' in op ? (
                <span className="font-mono text-[10px] text-red-400">drop: {op.column}</span>
              ) : (
                <span className="font-mono text-[10px] text-slate-600">select</span>
              )}
              <button onClick={() => remove(i)}><X className="h-3 w-3 text-slate-500 hover:text-red-400" /></button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
