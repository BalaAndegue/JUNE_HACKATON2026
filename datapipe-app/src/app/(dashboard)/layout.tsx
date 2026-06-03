'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { Sidebar } from '@/components/layout/Sidebar'
import { Navbar } from '@/components/layout/Navbar'
import { useAuthStore } from '@/store/auth.store'
import { authService } from '@/services/auth.service'
import { Skeleton } from '@/components/ui/skeleton'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const isEditor = pathname?.includes('/editor')
  const { isAuthenticated, isLoading, isDemoMode, setUser, clearAuth, setLoading } = useAuthStore()

  useEffect(() => {
    // Demo mode bypasses auth check
    if (isDemoMode) { setLoading(false); return }

    const check = async () => {
      try {
        const user = await authService.me()
        setUser(user)
      } catch {
        clearAuth()
        router.push('/login')
      }
    }
    if (!isAuthenticated) {
      check()
    } else {
      setLoading(false)
    }
  }, [isAuthenticated, isDemoMode, setUser, clearAuth, router, setLoading])

  if (isLoading) {
    return (
      <div className="flex h-screen bg-[#0a0a0a]">
        <div className="w-[220px] border-r border-[#1e1e1e] p-4 space-y-3">
          <Skeleton className="h-8 w-32" />
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
        </div>
        <div className="flex-1 p-6 space-y-4">
          <Skeleton className="h-10 w-64" />
          <div className="grid grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-32" />)}
          </div>
        </div>
      </div>
    )
  }

  return (
    // Tout l'écran est fixe — sidebar + contenu se partagent l'espace en flex
    <div className="flex h-screen overflow-hidden bg-[#0a0a0a]">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* La navbar est cachée sur l'éditeur pour lui donner toute la hauteur */}
        {!isEditor && <Navbar />}
        {/* overflow-hidden sur l'éditeur = canvas fixe ; overflow-auto ailleurs = scroll normal */}
        <main className={isEditor ? 'flex flex-1 overflow-hidden' : 'flex-1 overflow-auto'}>
          {children}
        </main>
      </div>
    </div>
  )
}
