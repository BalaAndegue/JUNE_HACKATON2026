import api from '@/lib/axios'
import type { Organisation, Member, Workspace, Role } from '@/types'

export const orgService = {
  create: async (data: { name: string; slug?: string; plan?: string }) => {
    const res = await api.post<Organisation>('/api/v1/orgs', data)
    return res.data
  },

  list: async () => {
    const res = await api.get<{ orgs: Organisation[] }>('/api/v1/orgs')
    return res.data.orgs
  },

  get: async (orgId: string) => {
    const res = await api.get<Organisation>(`/api/v1/orgs/${orgId}`)
    return res.data
  },

  update: async (orgId: string, data: { name?: string; settings?: Record<string, unknown> }) => {
    const res = await api.patch<Organisation>(`/api/v1/orgs/${orgId}`, data)
    return res.data
  },

  delete: async (orgId: string) => {
    await api.delete(`/api/v1/orgs/${orgId}`)
  },

  // Members
  inviteMember: async (orgId: string, email: string, role: Role) => {
    const res = await api.post(`/api/v1/orgs/${orgId}/members/invite`, { email, role })
    return res.data as { invite_id: string; email: string; expires_at: string }
  },

  getMembers: async (orgId: string) => {
    const res = await api.get<{ members: Member[] }>(`/api/v1/orgs/${orgId}/members`)
    return res.data.members
  },

  updateMemberRole: async (orgId: string, userId: string, role: Role) => {
    await api.patch(`/api/v1/orgs/${orgId}/members/${userId}`, { role })
  },

  removeMember: async (orgId: string, userId: string) => {
    await api.delete(`/api/v1/orgs/${orgId}/members/${userId}`)
  },

  acceptInvite: async (orgId: string, token: string) => {
    await api.post(`/api/v1/orgs/${orgId}/members/accept-invite`, { token })
  },

  // Workspaces
  getWorkspaces: async (orgId: string) => {
    const res = await api.get<{ workspaces: Workspace[] }>(`/api/v1/orgs/${orgId}/workspaces`)
    return res.data.workspaces
  },

  createWorkspace: async (orgId: string, data: { name: string; description?: string; color?: string }) => {
    const res = await api.post<Workspace>(`/api/v1/orgs/${orgId}/workspaces`, data)
    return res.data
  },

  updateWorkspace: async (orgId: string, wsId: string, data: Partial<Workspace>) => {
    const res = await api.patch<Workspace>(`/api/v1/orgs/${orgId}/workspaces/${wsId}`, data)
    return res.data
  },

  deleteWorkspace: async (orgId: string, wsId: string) => {
    await api.delete(`/api/v1/orgs/${orgId}/workspaces/${wsId}`)
  },
}
