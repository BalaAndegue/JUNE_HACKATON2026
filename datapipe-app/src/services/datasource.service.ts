import api from '@/lib/axios'
import type { Datasource, DatasourceType, TableInfo, ColumnSchema } from '@/types'

export const datasourceService = {
  create: async (data: {
    name: string
    type: DatasourceType
    host?: string
    port?: number
    database?: string
    username?: string
    password?: string
  }) => {
    const res = await api.post<Datasource>('/api/v1/datasources', data)
    return res.data
  },

  list: async () => {
    const res = await api.get<{ datasources: Datasource[] }>('/api/v1/datasources')
    return res.data.datasources
  },

  update: async (dsId: string, data: Partial<Datasource> & { password?: string }) => {
    const res = await api.patch<Datasource>(`/api/v1/datasources/${dsId}`, data)
    return res.data
  },

  delete: async (dsId: string) => {
    await api.delete(`/api/v1/datasources/${dsId}`)
  },

  test: async (dsId: string) => {
    const res = await api.post(`/api/v1/datasources/${dsId}/test`)
    return res.data as { success: boolean; latency_ms: number; server_version: string }
  },

  getTables: async (dsId: string) => {
    const res = await api.get<{ tables: TableInfo[] }>(`/api/v1/datasources/${dsId}/tables`)
    return res.data.tables
  },

  getTableSchema: async (dsId: string, table: string) => {
    const res = await api.get<{ columns: ColumnSchema[] }>(`/api/v1/datasources/${dsId}/tables/${table}/schema`)
    return res.data.columns
  },

  getTablePreview: async (dsId: string, table: string) => {
    const res = await api.get(`/api/v1/datasources/${dsId}/tables/${table}/preview`)
    return res.data
  },

  query: async (dsId: string, sql: string, limit = 500) => {
    const res = await api.post(`/api/v1/datasources/${dsId}/query`, { sql, limit })
    return res.data
  },

  sync: async (dsId: string) => {
    await api.post(`/api/v1/datasources/${dsId}/sync`)
  },
}
