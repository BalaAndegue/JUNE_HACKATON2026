import api from '@/lib/axios'
import type { Webhook, WebhookDelivery } from '@/types'

export const webhookService = {
  list: async () => {
    const res = await api.get<{ webhooks: Webhook[] }>('/api/v1/webhooks')
    return res.data.webhooks
  },

  create: async (data: {
    name: string
    url: string
    events: string[]
    secret?: string
    headers?: Record<string, string>
  }) => {
    const res = await api.post<Webhook>('/api/v1/webhooks', data)
    return res.data
  },

  update: async (webhookId: string, data: Partial<Webhook>) => {
    const res = await api.patch<Webhook>(`/api/v1/webhooks/${webhookId}`, data)
    return res.data
  },

  delete: async (webhookId: string) => {
    await api.delete(`/api/v1/webhooks/${webhookId}`)
  },

  test: async (webhookId: string) => {
    const res = await api.post(`/api/v1/webhooks/${webhookId}/test`)
    return res.data as { delivered: boolean; response_status: number; response_time_ms: number }
  },

  get: async (webhookId: string) => {
    const res = await api.get<Webhook>(`/api/v1/webhooks/${webhookId}`)
    return res.data
  },

  getDeliveries: async (webhookId: string) => {
    const res = await api.get<{ deliveries: WebhookDelivery[] }>(`/api/v1/webhooks/${webhookId}/deliveries`)
    return res.data.deliveries
  },

  retryDelivery: async (webhookId: string, deliveryId: string) => {
    await api.post(`/api/v1/webhooks/${webhookId}/deliveries/${deliveryId}/retry`)
  },
}
