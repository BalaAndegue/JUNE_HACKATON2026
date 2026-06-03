'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import api from '@/lib/axios'
import { authService } from '@/services/auth.service'
import { useAuthStore } from '@/store/auth.store'

const DEMO = { email: 'demo@bank.cm', password: 'Hackaton2026!' }

/**
 * One-click demo: logs into the seeded banking account on the REAL backend and
 * drops straight into the seeded pipeline editor (real engine, real data).
 */
export default function DemoPage() {
  const router = useRouter()
  const setUser = useAuthStore((s) => s.setUser)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const boot = async () => {
      try {
        await authService.login(DEMO)
        const me = await authService.me()
        if (cancelled) return
        setUser(me)

        // Resolve the seeded pipeline and open its editor directly.
        const orgs = (await api.get('/api/v1/orgs')).data.orgs
        const orgId = orgs[0].id
        const ws = (await api.get(`/api/v1/orgs/${orgId}/workspaces`)).data.workspaces[0].id
        const pipes = (await api.get(`/api/v1/pipelines?workspace_id=${ws}`)).data.data
        if (cancelled) return
        if (pipes.length > 0) {
          router.replace(`/dashboard/pipelines/${pipes[0].id}/editor`)
        } else {
          router.replace('/dashboard')
        }
      } catch {
        if (!cancelled) {
          setError("Backend injoignable. Vérifiez que l'API tourne sur le port 5000.")
        }
      }
    }
    boot()
    return () => { cancelled = true }
  }, [router, setUser])

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f4f6f9]">
      <div className="flex flex-col items-center gap-4">
        <Image src="/logo.png" alt="DataPipe" width={64} height={64}
               className="rounded-2xl animate-pulse" />
        {error ? (
          <p className="max-w-xs text-center text-sm text-red-500">{error}</p>
        ) : (
          <p className="text-sm text-slate-500">Connexion au mode démo…</p>
        )}
      </div>
    </div>
  )
}
