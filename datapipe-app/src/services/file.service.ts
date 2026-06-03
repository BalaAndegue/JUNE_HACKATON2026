import api from '@/lib/axios'
import type { DataFile, ColumnSchema } from '@/types'

export const fileService = {
  upload: async (file: File, options?: { encoding?: string; separator?: string }, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    if (options?.encoding) form.append('encoding', options.encoding)
    if (options?.separator) form.append('separator', options.separator)

    const res = await api.post<DataFile>('/api/v1/files/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) onProgress?.(Math.round((e.loaded * 100) / e.total))
      },
    })
    return res.data
  },

  list: async () => {
    const res = await api.get<{ files: DataFile[] }>('/api/v1/files')
    return res.data.files
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
