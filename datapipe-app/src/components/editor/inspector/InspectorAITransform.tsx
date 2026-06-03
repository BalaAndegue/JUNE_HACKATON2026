'use client'

import { useState } from 'react'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sparkles, Loader2, Code2, Copy } from 'lucide-react'
import { toast } from 'sonner'
import type { AITransformConfig } from '@/types/nodeConfigs'

const PROMPT_EXAMPLES = [
  'Convertis la colonne "date" en format DD/MM/YYYY',
  'Crée une colonne "tranche_age" à partir de la colonne "age" (0-18, 19-35, 36-60, 60+)',
  'Normalise les montants en euros : divise par 100 si > 10000',
  'Extrait le prénom et le nom de la colonne "nom_complet"',
]

interface Props {
  config: AITransformConfig
  onChange: (cfg: AITransformConfig) => void
  onGenerateCode?: (prompt: string, model: string) => Promise<string>
}

export function InspectorAITransform({ config, onChange, onGenerateCode }: Props) {
  const update = (patch: Partial<AITransformConfig>) => onChange({ ...config, ...patch })
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerate = async () => {
    if (!config.prompt || !onGenerateCode) return
    setIsGenerating(true)
    try {
      const code = await onGenerateCode(config.prompt, config.model ?? 'claude-sonnet-4-6')
      update({ generated_code: code })
      toast.success('Code généré')
    } catch {
      toast.error('Erreur lors de la génération')
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Model */}
      <div className="space-y-1.5">
        <Label>Modèle IA</Label>
        <Select
          value={config.model ?? 'claude-sonnet-4-6'}
          onValueChange={(v) => update({ model: v as AITransformConfig['model'] })}
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="claude-sonnet-4-6">Claude Sonnet 4.6 — Recommandé</SelectItem>
            <SelectItem value="claude-haiku-4-5">Claude Haiku 4.5 — Plus rapide</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Prompt */}
      <div className="space-y-1.5">
        <Label>Description de la transformation <span className="text-[#ff6d35]">*</span></Label>
        <Textarea
          className="min-h-[100px] resize-none"
          placeholder="Décrivez en français ce que vous voulez faire avec les données…"
          value={config.prompt ?? ''}
          onChange={(e) => update({ prompt: e.target.value })}
        />
      </div>

      {/* Quick examples */}
      <div className="space-y-1.5">
        <Label className="text-[10px] uppercase tracking-widest text-gray-700">Exemples</Label>
        <div className="space-y-1">
          {PROMPT_EXAMPLES.map((ex, i) => (
            <button
              key={i}
              className="w-full text-left rounded-md px-2.5 py-1.5 text-[11px] text-slate-500 hover:bg-[#ffffff] hover:text-slate-700 transition-colors"
              onClick={() => update({ prompt: ex })}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Generate button */}
      {onGenerateCode && (
        <Button
          className="w-full gap-2"
          onClick={handleGenerate}
          disabled={!config.prompt || isGenerating}
        >
          {isGenerating ? (
            <><Loader2 className="h-4 w-4 animate-spin" /> Génération…</>
          ) : (
            <><Sparkles className="h-4 w-4" /> Générer le code</>
          )}
        </Button>
      )}

      {/* Generated code */}
      {config.generated_code && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label className="flex items-center gap-1.5">
              <Code2 className="h-3.5 w-3.5" /> Code généré
            </Label>
            <Button
              size="icon-sm"
              variant="ghost"
              onClick={() => { navigator.clipboard.writeText(config.generated_code!); toast.success('Copié !') }}
            >
              <Copy className="h-3.5 w-3.5" />
            </Button>
          </div>
          <pre className="rounded-lg bg-[#f4f6f9] border border-[#d7dbe2] p-3 text-[10px] text-emerald-400 font-mono overflow-auto max-h-48 whitespace-pre-wrap">
            {config.generated_code}
          </pre>
        </div>
      )}
    </div>
  )
}
