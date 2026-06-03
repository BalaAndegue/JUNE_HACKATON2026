'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, GitBranch, FileUp, BarChart3, Settings,
  Bell, Key, Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useNotificationStore } from '@/store/notification.store'
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

  return (
    <aside className="flex h-full w-[220px] flex-col border-r border-[#1e1e1e] bg-[#0a0a0a]">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 border-b border-[#1e1e1e] px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#ff6d35]">
          <Zap className="h-4 w-4 text-white" fill="white" />
        </div>
        <span className="text-sm font-bold tracking-tight text-gray-100">DataPipe</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-[#ff6d35]/15 text-[#ff6d35]'
                  : 'text-gray-500 hover:bg-[#141414] hover:text-gray-300'
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              <span className="flex-1">{item.label}</span>
              {item.badge && unreadCount > 0 && (
                <Badge variant="destructive" className="h-4 min-w-4 px-1 text-[10px]">
                  {unreadCount}
                </Badge>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Bottom */}
      <div className="border-t border-[#1e1e1e] p-3">
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-gray-600">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          API connectée
        </div>
      </div>
    </aside>
  )
}
