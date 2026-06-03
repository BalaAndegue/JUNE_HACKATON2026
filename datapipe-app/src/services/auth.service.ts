import api, { tokenStore } from '@/lib/axios'
import type { AuthTokens, User, Session } from '@/types'

export const authService = {
  register: async (data: { email: string; password: string; name: string; org_name?: string }) => {
    const res = await api.post('/api/v1/auth/register', data)
    return res.data as { user: User; message: string }
  },

  login: async (data: { email: string; password: string }) => {
    const res = await api.post<AuthTokens>('/api/v1/auth/login', data, { withCredentials: true })
    tokenStore.set(res.data.access_token)
    return res.data
  },

  logout: async (refresh_token?: string) => {
    await api.post('/api/v1/auth/logout', { refresh_token }, { withCredentials: true })
    tokenStore.clear()
  },

  refreshToken: async () => {
    const res = await api.post<{ access_token: string; expires_in: number }>(
      '/api/v1/auth/refresh-token',
      {},
      { withCredentials: true }
    )
    tokenStore.set(res.data.access_token)
    return res.data
  },

  me: async () => {
    const res = await api.get<User>('/api/v1/auth/me')
    return res.data
  },

  updateProfile: async (data: { name?: string; avatar_url?: string }) => {
    const res = await api.patch<User>('/api/v1/auth/me', data)
    return res.data
  },

  changePassword: async (data: { current_password: string; new_password: string }) => {
    const res = await api.post('/api/v1/auth/change-password', data)
    return res.data as { message: string }
  },

  forgotPassword: async (email: string) => {
    const res = await api.post('/api/v1/auth/forgot-password', { email })
    return res.data as { message: string }
  },

  resetPassword: async (data: { token: string; new_password: string }) => {
    const res = await api.post('/api/v1/auth/reset-password', data)
    return res.data as { message: string }
  },

  verifyEmail: async (token: string) => {
    const res = await api.post('/api/v1/auth/verify-email', { token })
    if (res.data.access_token) tokenStore.set(res.data.access_token)
    return res.data as { message: string; access_token?: string }
  },

  getSessions: async () => {
    const res = await api.get('/api/v1/auth/sessions')
    return res.data.sessions as Session[]
  },

  revokeSession: async (sessionId: string) => {
    const res = await api.delete(`/api/v1/auth/sessions/${sessionId}`)
    return res.data as { message: string }
  },

  revokeAllSessions: async (exceptCurrent = true) => {
    const res = await api.post('/api/v1/auth/revoke-all-sessions', { except_current: exceptCurrent })
    return res.data as { revoked_count: number; message: string }
  },

  deleteAccount: async (password: string) => {
    const res = await api.delete('/api/v1/auth/me', { data: { password } })
    tokenStore.clear()
    return res.data as { message: string }
  },
}
