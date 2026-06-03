import api from '@/lib/axios'
import type { ApiKey, Integration } from '@/types'

export const apikeyService = {
  list: async () => {
    const res = await api.get<{ api_keys: ApiKey[] }>('/api/v1/api-keys')
    return res.data.api_keys
  },

  create: async (data: { name: string; scopes: string[] }) => {
    const res = await api.post<ApiKey & { key: string; warning: string }>('/api/v1/api-keys', data)
    return res.data
  },

  revoke: async (keyId: string) => {
    await api.delete(`/api/v1/api-keys/${keyId}`)
  },

  rotate: async (keyId: string) => {
    const res = await api.post(`/api/v1/api-keys/${keyId}/rotate`)
    return res.data as { new_key: string; rotated_at: string }
  },

  // Integrations
  listIntegrations: async () => {
    const res = await api.get<{ integrations: Integration[] }>('/api/v1/integrations')
    return res.data.integrations
  },

  connect: async (slug: string, data: { auth_code?: string; credentials?: Record<string, string> }) => {
    const res = await api.post(`/api/v1/integrations/${slug}/connect`, data)
    return res.data as { connected: boolean; account: string }
  },

  disconnect: async (slug: string) => {
    await api.delete(`/api/v1/integrations/${slug}/disconnect`)
  },

  getIntegrationStatus: async (slug: string) => {
    const res = await api.get(`/api/v1/integrations/${slug}/status`)
    return res.data as { connected: boolean; healthy: boolean; account: string }
  },
}
