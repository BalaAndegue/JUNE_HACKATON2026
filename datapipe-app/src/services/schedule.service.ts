import api from '@/lib/axios'
import type { Schedule, Run } from '@/types'

export const scheduleService = {
  list: async (pipelineId: string) => {
    const res = await api.get<{ schedules: Schedule[] }>(`/api/v1/pipelines/${pipelineId}/schedules`)
    return res.data.schedules
  },

  create: async (pipelineId: string, data: {
    name: string
    cron: string
    timezone?: string
    enabled?: boolean
    notify_on_failure?: boolean
  }) => {
    const res = await api.post<Schedule>(`/api/v1/pipelines/${pipelineId}/schedules`, data)
    return res.data
  },

  update: async (pipelineId: string, schedId: string, data: { cron?: string; timezone?: string; name?: string }) => {
    const res = await api.patch<Schedule>(`/api/v1/pipelines/${pipelineId}/schedules/${schedId}`, data)
    return res.data
  },

  delete: async (pipelineId: string, schedId: string) => {
    await api.delete(`/api/v1/pipelines/${pipelineId}/schedules/${schedId}`)
  },

  pause: async (pipelineId: string, schedId: string) => {
    const res = await api.post(`/api/v1/pipelines/${pipelineId}/schedules/${schedId}/pause`)
    return res.data as { status: string; next_run_at: null }
  },

  resume: async (pipelineId: string, schedId: string) => {
    const res = await api.post(`/api/v1/pipelines/${pipelineId}/schedules/${schedId}/resume`)
    return res.data as { status: string; next_run_at: string }
  },

  trigger: async (pipelineId: string, schedId: string) => {
    const res = await api.post(`/api/v1/pipelines/${pipelineId}/schedules/${schedId}/trigger`)
    return res.data as { run_id: string; triggered_by: string }
  },

  getHistory: async (pipelineId: string, schedId: string) => {
    const res = await api.get<{ history: Array<{ run_id: string; status: string; triggered_at: string }> }>(
      `/api/v1/pipelines/${pipelineId}/schedules/${schedId}/history`
    )
    return res.data.history
  },

  get: async (pipelineId: string, schedId: string) => {
    const res = await api.get<Schedule>(`/api/v1/pipelines/${pipelineId}/schedules/${schedId}`)
    return res.data
  },
}
