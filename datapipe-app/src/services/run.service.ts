import api from '@/lib/axios'
import type { Run, NodeRun, DataPreview, NodeStats, LogEntry, PaginatedResponse, RunStatus, NodeResult } from '@/types'

export const runService = {
  execute: async (pipelineId: string, params?: {
    mode?: 'full' | 'from_node'
    from_node?: string
    params?: Record<string, unknown>
  }) => {
    // The backend runs synchronously and returns the full node_results.
    const res = await api.post<{
      run_id: string
      status: RunStatus
      pipeline_id: string
      started_at: string
      finished_at?: string
      duration_ms?: number
      node_results: Record<string, NodeResult>
    }>(`/api/v1/pipelines/${pipelineId}/execute`, params ?? {})
    return res.data
  },

  dryRun: async (pipelineId: string) => {
    const res = await api.post(`/api/v1/pipelines/${pipelineId}/execute/dry-run`)
    return res.data as {
      valid: boolean
      warnings: string[]
      estimated_duration_s: number
      estimated_rows_processed: number
    }
  },

  executeNode: async (pipelineId: string, nodeId: string, usePinnedData = true) => {
    const res = await api.post(`/api/v1/pipelines/${pipelineId}/execute/node/${nodeId}`, {
      use_pinned_data: usePinnedData,
    })
    return res.data
  },

  listRuns: async (params?: {
    pipeline_id?: string
    status?: RunStatus
    page?: number
    per_page?: number
  }) => {
    const res = await api.get<PaginatedResponse<Run>>('/api/v1/runs', { params })
    return res.data
  },

  getRun: async (runId: string) => {
    const res = await api.get<Run>(`/api/v1/runs/${runId}`)
    return res.data
  },

  cancel: async (runId: string) => {
    const res = await api.post(`/api/v1/runs/${runId}/cancel`)
    return res.data as { status: RunStatus; cancelled_at: string }
  },

  retry: async (runId: string, fromBeginning = false) => {
    const res = await api.post(`/api/v1/runs/${runId}/retry`, { from_beginning: fromBeginning })
    return res.data as { new_run_id: string; status: RunStatus }
  },

  deleteRun: async (runId: string) => {
    await api.delete(`/api/v1/runs/${runId}`)
  },

  getNodeRuns: async (runId: string) => {
    const res = await api.get<{ nodes: NodeRun[] }>(`/api/v1/runs/${runId}/nodes`)
    return res.data.nodes
  },

  getNodeRun: async (runId: string, nodeId: string) => {
    const res = await api.get<NodeRun>(`/api/v1/runs/${runId}/nodes/${nodeId}`)
    return res.data
  },

  getNodePreview: async (runId: string, nodeId: string, limit = 50, offset = 0) => {
    const res = await api.get<DataPreview>(`/api/v1/runs/${runId}/nodes/${nodeId}/preview`, {
      params: { limit, offset },
    })
    return res.data
  },

  getNodeStats: async (runId: string, nodeId: string) => {
    const res = await api.get<NodeStats>(`/api/v1/runs/${runId}/nodes/${nodeId}/stats`)
    return res.data
  },

  getLogs: async (runId: string) => {
    const res = await api.get<{ logs: LogEntry[] }>(`/api/v1/runs/${runId}/logs`)
    return res.data.logs
  },

  getResult: async (runId: string) => {
    const res = await api.get(`/api/v1/runs/${runId}/result`)
    return res.data
  },

  getNodeResult: async (runId: string, nodeId: string) => {
    const res = await api.get(`/api/v1/runs/${runId}/result/nodes/${nodeId}`)
    return res.data
  },

  // Banking compliance audit report (exportable)
  getAuditReport: async (runId: string) => {
    const res = await api.get(`/api/v1/runs/${runId}/audit-report`)
    return res.data as Record<string, unknown>
  },

  // SSE log streaming — returns EventSource
  streamLogs: (runId: string, onMessage: (log: LogEntry) => void, onEnd?: () => void) => {
    const token = typeof window !== 'undefined'
      ? (window as Window & { __datapipe_token?: string }).__datapipe_token
      : null
    const url = `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/runs/${runId}/logs/stream`
    const es = new EventSource(url)
    es.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)) } catch {}
    }
    es.onerror = () => { es.close(); onEnd?.() }
    return es
  },
}
