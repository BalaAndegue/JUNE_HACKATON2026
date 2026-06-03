import api from '@/lib/axios'
import type { PipelineAnalytics, RunTrend, NodeBottleneck, WorkspaceUsage } from '@/types'

export const analyticsService = {
  getPipelineMetrics: async (pipelineId: string, period: '7d' | '30d' | '90d' = '30d') => {
    const res = await api.get<PipelineAnalytics>(`/api/v1/analytics/pipelines/${pipelineId}`, {
      params: { period },
    })
    return res.data
  },

  getRunTrend: async (pipelineId: string, period: '7d' | '30d' | '90d' = '30d') => {
    const res = await api.get<{ trend: RunTrend[] }>(
      `/api/v1/analytics/pipelines/${pipelineId}/runs/trend`,
      { params: { period } }
    )
    return res.data.trend
  },

  getBottlenecks: async (pipelineId: string) => {
    const res = await api.get<{ bottlenecks: NodeBottleneck[] }>(
      `/api/v1/analytics/pipelines/${pipelineId}/nodes/bottlenecks`
    )
    return res.data.bottlenecks
  },

  getWorkspaceUsage: async () => {
    const res = await api.get<WorkspaceUsage>('/api/v1/analytics/workspace/usage')
    return res.data
  },

  getWorkspaceCosts: async () => {
    const res = await api.get('/api/v1/analytics/workspace/costs')
    return res.data
  },

  getAuditLogs: async (params?: {
    resource?: string
    action?: string
    user_id?: string
    from?: string
    to?: string
    page?: number
  }) => {
    const res = await api.get('/api/v1/audit-logs', { params })
    return res.data
  },
}
