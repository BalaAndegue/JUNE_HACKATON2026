import api from '@/lib/axios'
import type { SystemLimits } from '@/types'

export const systemService = {
  health: async () => {
    const res = await api.get('/health')
    return res.data as { status: string; version: string; uptime_s: number }
  },

  getVersion: async () => {
    const res = await api.get('/api/v1/system/version')
    return res.data as { version: string; build: string; deployed_at: string }
  },

  getLimits: async () => {
    const res = await api.get<SystemLimits>('/api/v1/system/limits')
    return res.data
  },
}
