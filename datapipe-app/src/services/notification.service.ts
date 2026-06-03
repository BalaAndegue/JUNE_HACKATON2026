import api from '@/lib/axios'
import type { Notification } from '@/types'

export const notificationService = {
  list: async (unreadOnly = false, page = 1) => {
    const res = await api.get<{ notifications: Notification[]; unread_count: number }>('/api/v1/notifications', {
      params: { unread_only: unreadOnly, page },
    })
    return res.data
  },

  markRead: async (notifId: string) => {
    await api.patch(`/api/v1/notifications/${notifId}/read`)
  },

  markAllRead: async () => {
    await api.post('/api/v1/notifications/read-all')
  },

  delete: async (notifId: string) => {
    await api.delete(`/api/v1/notifications/${notifId}`)
  },

  // Alerts
  listAlerts: async () => {
    const res = await api.get('/api/v1/alerts')
    return res.data
  },

  createAlert: async (data: {
    name: string
    pipeline_id: string
    condition: string
    threshold?: number
    channels: string[]
    recipients?: string[]
  }) => {
    const res = await api.post('/api/v1/alerts', data)
    return res.data
  },

  getAlert: async (alertId: string) => {
    const res = await api.get(`/api/v1/alerts/${alertId}`)
    return res.data
  },

  updateAlert: async (alertId: string, data: Record<string, unknown>) => {
    const res = await api.patch(`/api/v1/alerts/${alertId}`, data)
    return res.data
  },

  deleteAlert: async (alertId: string) => {
    await api.delete(`/api/v1/alerts/${alertId}`)
  },

  muteAlert: async (alertId: string, until?: string) => {
    const res = await api.post(`/api/v1/alerts/${alertId}/mute`, { until })
    return res.data as { muted_until: string }
  },
}
