'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import Image from 'next/image'
import {
  LayoutDashboard, GitBranch, FileUp, BarChart3, Settings,
  Bell, Key, ChevronLeft,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useNotificationStore } from '@/store/notification.store'
import { useUIStore } from '@/store/ui.store'
import { Badge } from '@/components/ui/badge'

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { label: 'Pipelines', icon: GitBranch, href: '/dashboard/pipelines' },
  { label: 'Fichiers', icon: FileUp, href: '/dashboard/files' },
  { label: 'Analytics', icon: BarChart3, href: '/dashboard/analytics' },

  { label: 'Notifications', icon: Bell, href: '/dashboard/notifications', badge: true },
  { label: 'API Keys', icon: Key, href: '/dashboard/settings/api-keys' },
  { label: 'Paramètres', icon: Settings, href: '/dashboard/settings' },
]

export function Sidebar() {
  const pathname = usePathname()
  const unreadCount = useNotificationStore((s) => s.unreadCount)
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  return (
    <aside className={cn(
      'flex h-full flex-col border-r border-[#1e1e1e] bg-[#0a0a0a] transition-all duration-300',
      sidebarCollapsed ? 'w-16' : 'w-[220px]'
    )}>
      {/* Logo / toggle */}
      <div className="flex h-14 items-center border-b border-[#1e1e1e] px-3">
        {sidebarCollapsed ? (
          /* Collapsed : uniquement le bouton pour réouvrir, centré */
          <button
            onClick={toggleSidebar}
            className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 hover:bg-[#141414] hover:text-gray-300 transition-colors mx-auto"
            title="Déplier la sidebar"
          >
            <ChevronLeft className="h-4 w-4 rotate-180" />
          </button>
        ) : (
          /* Expanded : logo + nom + bouton collapse */
          <>
            <div className="flex flex-1 items-center gap-2.5 min-w-0">
              <Image src="/logo.png" alt="DataPipe" width={44} height={44} className="rounded-lg shrink-0" />
              <span className="text-sm font-bold tracking-tight text-gray-100 truncate">DataPipe</span>
            </div>
            <button
              onClick={toggleSidebar}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-gray-500 hover:bg-[#141414] hover:text-gray-300 transition-colors"
              title="Réduire la sidebar"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          </>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))
          return (
            <Link
              key={item.href}
              href={item.href}
              title={sidebarCollapsed ? item.label : undefined}
              className={cn(
                'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-[#ff6d35]/15 text-[#ff6d35]'
                  : 'text-gray-500 hover:bg-[#141414] hover:text-gray-300',
                sidebarCollapsed && 'justify-center'
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!sidebarCollapsed && (
                <>
                  <span className="flex-1">{item.label}</span>
                  {item.badge && unreadCount > 0 && (
                    <Badge variant="destructive" className="h-4 min-w-4 px-1 text-[10px]">
                      {unreadCount}
                    </Badge>
                  )}
                </>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Bottom */}
      <div className="border-t border-[#1e1e1e] p-3">
        <div className={cn('flex items-center rounded-md px-2 py-1.5 text-xs text-gray-600 transition-all', sidebarCollapsed && 'justify-center')}>
          <span className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
          {!sidebarCollapsed && <span className="ml-2">API connectée</span>}
        </div>
      </div>
    </aside>
  )
}
