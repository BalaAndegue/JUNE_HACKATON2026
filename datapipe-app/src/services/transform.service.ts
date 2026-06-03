import api from '@/lib/axios'
import type { FilterValidation, SQLValidation, JoinPreview, DuckDBFunction, ColumnSchema } from '@/types'

export const transformService = {
  validateFilter: async (expression: string, schema: ColumnSchema[]) => {
    const res = await api.post<FilterValidation>('/api/v1/transform/filter/validate', { expression, schema })
    return res.data
  },

  validateSQL: async (sql: string, schema?: ColumnSchema[]) => {
    const res = await api.post<SQLValidation>('/api/v1/transform/sql/validate', { sql, schema })
    return res.data
  },

  explainSQL: async (sql: string, data?: unknown[]) => {
    const res = await api.post('/api/v1/transform/sql/explain', { sql, data })
    return res.data as { plan: string; estimated_rows: number; estimated_duration_ms: number }
  },

  formatSQL: async (sql: string) => {
    const res = await api.post('/api/v1/transform/sql/format', { sql })
    return res.data.formatted as string
  },

  inferSchema: async (sample: unknown[]) => {
    const res = await api.post('/api/v1/transform/schema/infer', { sample })
    return res.data as { columns: ColumnSchema[] }
  },

  castSchema: async (casts: Array<{ column: string; from: string; to: string }>) => {
    const res = await api.post('/api/v1/transform/schema/cast', { casts })
    return res.data.sql as string
  },

  previewJoin: async (data: {
    left_file_id: string
    right_file_id: string
    left_key: string
    right_key: string
    join_type: 'LEFT' | 'INNER' | 'OUTER'
  }) => {
    const res = await api.post<JoinPreview>('/api/v1/transform/join/preview', data)
    return res.data
  },

  previewAggregate: async (data: {
    file_id: string
    group_by: string[]
    aggregates: Array<{ column: string; func: string; alias: string }>
  }) => {
    const res = await api.post('/api/v1/transform/aggregate/preview', data)
    return res.data
  },

  getFunctions: async () => {
    const res = await api.get<{ functions: DuckDBFunction[] }>('/api/v1/transform/functions')
    return res.data.functions
  },

  generateMockData: async (data: {
    schema: Array<{ name: string; type: string; range?: [number, number] }>
    rows: number
    domain?: string
    locale?: string
  }) => {
    const res = await api.post('/api/v1/transform/mock-data/generate', data)
    return res.data
  },
}
