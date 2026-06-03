import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Token storage helpers (memory only for access_token — security best practice)
let accessToken: string | null = null

export const tokenStore = {
  get: () => accessToken,
  set: (t: string) => { accessToken = t },
  clear: () => { accessToken = null },
}

// Attach Bearer token on every request
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.get()
  if (token && config.headers) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true

      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((token: string) => {
            original.headers['Authorization'] = `Bearer ${token}`
            resolve(api(original))
          })
        })
      }

      isRefreshing = true
      try {
        const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh-token`, {}, {
          withCredentials: true,
        })
        const newToken: string = data.access_token
        tokenStore.set(newToken)
        refreshQueue.forEach((cb) => cb(newToken))
        refreshQueue = []
        original.headers['Authorization'] = `Bearer ${newToken}`
        return api(original)
      } catch {
        tokenStore.clear()
        if (typeof window !== 'undefined') window.location.href = '/login'
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default api
