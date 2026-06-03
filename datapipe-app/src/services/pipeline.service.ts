import api from '@/lib/axios'
import type { Pipeline, PipelineVersion, PipelineTemplate, PaginatedResponse } from '@/types'

export const pipelineService = {
  list: async (params: {
    workspace_id: string
    page?: number
    per_page?: number
    search?: string
    status?: string
    sort?: string
  }) => {
    const res = await api.get<PaginatedResponse<Pipeline>>('/api/v1/pipelines', { params })
    return res.data
  },

  create: async (data: { name: string; workspace_id: string; description?: string; tags?: string[] }) => {
    const res = await api.post<Pipeline>('/api/v1/pipelines', data)
    return res.data
  },

  get: async (id: string) => {
    const res = await api.get<Pipeline>(`/api/v1/pipelines/${id}`)
    return res.data
  },

  save: async (id: string, data: { name?: string; nodes: unknown[]; edges: unknown[] }) => {
    const res = await api.put<Pipeline>(`/api/v1/pipelines/${id}`, data)
    return res.data
  },

  patch: async (id: string, data: { name?: string; description?: string; tags?: string[] }) => {
    const res = await api.patch<Pipeline>(`/api/v1/pipelines/${id}`, data)
    return res.data
  },

  delete: async (id: string) => {
    await api.delete(`/api/v1/pipelines/${id}`)
  },

  duplicate: async (id: string, name?: string) => {
    const res = await api.post<Pipeline>(`/api/v1/pipelines/${id}/duplicate`, { name })
    return res.data
  },

  archive: async (id: string) => {
    const res = await api.post(`/api/v1/pipelines/${id}/archive`)
    return res.data as { status: string; schedules_suspended: number }
  },

  restore: async (id: string) => {
    await api.post(`/api/v1/pipelines/${id}/restore`)
  },

  publish: async (id: string) => {
    await api.post(`/api/v1/pipelines/${id}/publish`)
  },

  // Versioning
  getVersions: async (id: string) => {
    const res = await api.get<{ versions: PipelineVersion[] }>(`/api/v1/pipelines/${id}/versions`)
    return res.data.versions
  },

  getVersion: async (id: string, versionId: string) => {
    const res = await api.get<Pipeline>(`/api/v1/pipelines/${id}/versions/${versionId}`)
    return res.data
  },

  restoreVersion: async (id: string, versionId: string) => {
    await api.post(`/api/v1/pipelines/${id}/versions/${versionId}/restore`)
  },

  createSnapshot: async (id: string, label?: string) => {
    await api.post(`/api/v1/pipelines/${id}/versions/snapshot`, { label })
  },

  getDiff: async (id: string, versionA: string, versionB: string) => {
    const res = await api.get(`/api/v1/pipelines/${id}/diff`, { params: { version_a: versionA, version_b: versionB } })
    return res.data
  },

  // Templates
  getTemplates: async () => {
    const res = await api.get<{ templates: PipelineTemplate[] }>('/api/v1/pipelines/templates')
    return res.data.templates
  },

  instantiateTemplate: async (templateId: string, data: { name: string; workspace_id: string }) => {
    const res = await api.post<Pipeline>(`/api/v1/pipelines/templates/${templateId}/instantiate`, data)
    return res.data
  },

  importPipeline: async (pipelineJson: unknown) => {
    const res = await api.post<Pipeline>('/api/v1/pipelines/import', { pipeline_json: pipelineJson })
    return res.data
  },

  exportPipeline: async (id: string, format: 'json' | 'yaml' = 'json') => {
    const res = await api.get(`/api/v1/pipelines/${id}/export`, { params: { format } })
    return res.data
  },

  merge: async (data: { source_pipeline_id: string; target_pipeline_id: string; offset_x?: number; offset_y?: number }) => {
    const res = await api.post('/api/v1/pipelines/merge', data)
    return res.data
  },
}
