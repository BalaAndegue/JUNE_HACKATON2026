import api from '@/lib/axios'
import type { Export, ExportFormat } from '@/types'

export const exportService = {
  create: async (data: {
    run_id: string
    node_id: string
    format: ExportFormat
    options?: { separator?: string; encoding?: string; include_header?: boolean }
  }) => {
    const res = await api.post<Export>('/api/v1/exports', data)
    return res.data
  },

  get: async (exportId: string) => {
    const res = await api.get<Export>(`/api/v1/exports/${exportId}`)
    return res.data
  },

  list: async () => {
    const res = await api.get<{ exports: Export[] }>('/api/v1/exports')
    return res.data.exports
  },

  delete: async (exportId: string) => {
    await api.delete(`/api/v1/exports/${exportId}`)
  },

  getDownloadUrl: (exportId: string) => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
    return `${base}/api/v1/exports/${exportId}/download`
  },

  share: async (exportId: string, options?: { expires_in_hours?: number; password?: string }) => {
    const res = await api.post(`/api/v1/exports/${exportId}/share`, options ?? {})
    return res.data as { share_url: string; expires_at: string }
  },
}
