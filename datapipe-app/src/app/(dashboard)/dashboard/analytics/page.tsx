'use client'

import { useEffect, useState } from 'react'
import { TrendingUp, Clock, Rows3, CheckCircle2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { analyticsService } from '@/services/analytics.service'
import { aiService } from '@/services/ai.service'
import { formatDuration, formatNumber } from '@/lib/utils'
import type { WorkspaceUsage, AIUsage } from '@/types'

export default function AnalyticsPage() {
  const [usage, setUsage] = useState<WorkspaceUsage | null>(null)
  const [aiUsage, setAiUsage] = useState<AIUsage | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      analyticsService.getWorkspaceUsage(),
      aiService.getUsage(),
    ]).then(([u, ai]) => {
      setUsage(u)
      setAiUsage(ai)
    }).catch(() => {}).finally(() => setIsLoading(false))
  }, [])

  const storagePercent = usage ? Math.round((usage.storage_used_mb / usage.storage_limit_mb) * 100) : 0

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <h1 className="text-xl font-bold text-gray-100">Analytics</h1>

      {/* Workspace metrics */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {isLoading ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />) : (
          <>
            <MetricCard icon={<TrendingUp className="h-5 w-5 text-blue-400" />} label="Runs ce mois" value={String(usage?.runs_this_month ?? 0)} bg="bg-blue-500/10" />
            <MetricCard icon={<Rows3 className="h-5 w-5 text-emerald-400" />} label="Lignes traitées" value={formatNumber(usage?.rows_processed_this_month ?? 0)} bg="bg-emerald-500/10" />
            <MetricCard icon={<CheckCircle2 className="h-5 w-5 text-purple-400" />} label="Pipelines actifs" value={String(usage?.active_pipelines ?? 0)} bg="bg-purple-500/10" />
            <MetricCard icon={<Clock className="h-5 w-5 text-amber-400" />} label="Runs planifiés" value={String(usage?.scheduled_runs ?? 0)} bg="bg-amber-500/10" />
          </>
        )}
      </div>

      {/* Storage & AI quota */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-sm">Stockage</CardTitle></CardHeader>
          <CardContent className="space-y-3 pt-0">
            {isLoading ? <Skeleton className="h-16" /> : (
              <>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">{usage?.storage_used_mb} MB utilisés</span>
                  <span className="text-gray-600">{usage?.storage_limit_mb} MB</span>
                </div>
                <Progress value={storagePercent} className={storagePercent > 80 ? '[&>div]:bg-red-500' : ''} />
                <p className="text-xs text-gray-600">{storagePercent}% utilisé</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-sm">Quota IA (tokens)</CardTitle></CardHeader>
          <CardContent className="space-y-3 pt-0">
            {isLoading || !aiUsage ? <Skeleton className="h-16" /> : (
              <>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">{formatNumber(aiUsage.tokens_used)} tokens</span>
                  <span className="text-gray-600">{formatNumber(aiUsage.tokens_limit)}</span>
                </div>
                <Progress value={Math.round((aiUsage.tokens_used / aiUsage.tokens_limit) * 100)} />
                <div className="flex justify-between text-xs text-gray-600">
                  <span>Coût estimé : ${aiUsage.cost_usd.toFixed(2)}</span>
                  <span>{aiUsage.month}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 pt-1">
                  {Object.entries(aiUsage.breakdown).map(([k, v]) => (
                    <div key={k} className="rounded-md bg-[#141414] px-2 py-1.5 text-center">
                      <p className="text-[10px] text-gray-600 capitalize">{k.replace('_', ' ')}</p>
                      <p className="text-xs font-semibold text-gray-300">{formatNumber(v)}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function MetricCard({ icon, label, value, bg }: { icon: React.ReactNode; label: string; value: string; bg: string }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${bg}`}>{icon}</div>
        <div>
          <p className="text-xs text-gray-600">{label}</p>
          <p className="text-xl font-bold text-gray-100">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}
