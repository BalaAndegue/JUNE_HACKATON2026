'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/auth.store'
import { Zap } from 'lucide-react'

export default function DemoPage() {
  const router = useRouter()
  const enableDemoMode = useAuthStore((s) => s.enableDemoMode)

  useEffect(() => {
    enableDemoMode()
    router.push('/dashboard')
  }, [enableDemoMode, router])

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0a0a0b]">
      <div className="flex flex-col items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#ff6d35] animate-pulse">
          <Zap className="h-6 w-6 text-white" fill="white" />
        </div>
        <p className="text-sm text-gray-500">Chargement du mode démo…</p>
      </div>
    </div>
  )
}
