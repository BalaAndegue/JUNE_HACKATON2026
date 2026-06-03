import api from '@/lib/axios'
import type { DataFile, ColumnSchema } from '@/types'

// Backend File shape -> frontend DataFile shape.
function toDataFile(f: Record<string, unknown>): DataFile {
  return {
    id: String(f.id),
    name: String(f.name ?? f.original_name ?? ''),
    size_bytes: Number(f.size ?? 0),
    rows: f.rows_count as number | undefined,
    columns: f.columns_count as number | undefined,
    created_at: String(f.created_at ?? ''),
  }
}

export const fileService = {
  upload: async (file: File, workspaceId: string,
                 options?: { encoding?: string; separator?: string },
                 onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    form.append('workspace_id', workspaceId)   // requis par le backend
    if (options?.encoding) form.append('encoding', options.encoding)
    if (options?.separator) form.append('separator', options.separator)

    const res = await api.post<Record<string, unknown>>('/api/v1/files/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) onProgress?.(Math.round((e.loaded * 100) / e.total))
      },
    })
    return toDataFile(res.data)
  },

  list: async (workspaceId: string) => {
    const res = await api.get<{ data: Record<string, unknown>[] }>('/api/v1/files', {
      params: { workspace_id: workspaceId },
    })
    return (res.data.data ?? []).map(toDataFile)
  },

  get: async (fileId: string) => {
    const res = await api.get<DataFile>(`/api/v1/files/${fileId}`)
    return res.data
  },

  delete: async (fileId: string) => {
    await api.delete(`/api/v1/files/${fileId}`)
  },

  getSchema: async (fileId: string) => {
    const res = await api.get<{ columns: ColumnSchema[] }>(`/api/v1/files/${fileId}/schema`)
    return res.data.columns
  },

  getPreview: async (fileId: string, limit = 100, offset = 0) => {
    const res = await api.get(`/api/v1/files/${fileId}/preview`, { params: { limit, offset } })
    return res.data
  },

  reparse: async (fileId: string, options: { separator?: string; encoding?: string; header?: boolean }) => {
    const res = await api.post(`/api/v1/files/${fileId}/reparse`, options)
    return res.data as DataFile
  },
}
