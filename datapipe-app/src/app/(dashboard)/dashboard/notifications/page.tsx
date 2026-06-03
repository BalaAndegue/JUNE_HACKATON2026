'use client'

import { useEffect } from 'react'
import { Bell, CheckCheck, Trash2, GitBranch, AlertTriangle, UserPlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { useNotificationStore } from '@/store/notification.store'
import { notificationService } from '@/services/notification.service'
import { getRelativeTime, cn } from '@/lib/utils'
import { toast } from 'sonner'
import type { Notification } from '@/types'

const typeConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  run_failed: { icon: <AlertTriangle className="h-4 w-4" />, color: 'text-red-400' },
  run_success: { icon: <GitBranch className="h-4 w-4" />, color: 'text-emerald-400' },
  member_joined: { icon: <UserPlus className="h-4 w-4" />, color: 'text-blue-400' },
  alert_triggered: { icon: <AlertTriangle className="h-4 w-4" />, color: 'text-amber-400' },
}

export default function NotificationsPage() {
  const { notifications, setNotifications, markRead, markAllRead, removeNotification } = useNotificationStore()
  const isLoading = notifications.length === 0

  useEffect(() => {
    notificationService.list().then((r) => setNotifications(r.notifications, r.unread_count)).catch(() => {})
  }, [setNotifications])

  const handleMarkRead = async (n: Notification) => {
    if (n.read) return
    try {
      await notificationService.markRead(n.id)
      markRead(n.id)
    } catch {}
  }

  const handleMarkAllRead = async () => {
    try {
      await notificationService.markAllRead()
      markAllRead()
      toast.success('Tout marqué comme lu')
    } catch {}
  }

  const handleDelete = async (n: Notification) => {
    try {
      await notificationService.delete(n.id)
      removeNotification(n.id)
    } catch {}
  }

  const unread = notifications.filter((n) => !n.read).length

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-gray-100">Notifications</h1>
          {unread > 0 && <Badge variant="destructive">{unread} non lues</Badge>}
        </div>
        {unread > 0 && (
          <Button variant="ghost" size="sm" onClick={handleMarkAllRead} className="gap-2 text-xs">
            <CheckCheck className="h-3.5 w-3.5" /> Tout marquer comme lu
          </Button>
        )}
      </div>

      {notifications.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
          <Bell className="h-10 w-10 text-gray-700" />
          <p className="text-sm text-gray-600">Aucune notification</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {notifications.map((n) => {
            const cfg = typeConfig[n.type] ?? typeConfig['run_success']
            return (
              <div
                key={n.id}
                className={cn(
                  'flex items-start gap-3 rounded-lg border px-4 py-3 cursor-pointer transition-colors',
                  n.read ? 'border-[#1a1a1a] bg-transparent' : 'border-[#2a2a2a] bg-[#111111]'
                )}
                onClick={() => handleMarkRead(n)}
              >
                <div className={cn('mt-0.5 shrink-0', cfg.color)}>{cfg.icon}</div>
                <div className="flex-1 min-w-0">
                  <p className={cn('text-sm', n.read ? 'text-gray-500' : 'text-gray-200')}>{n.message}</p>
                  <p className="text-xs text-gray-700 mt-0.5">{getRelativeTime(n.created_at)}</p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {!n.read && <span className="h-2 w-2 rounded-full bg-[#ff6d35]" />}
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={(e) => { e.stopPropagation(); handleDelete(n) }}
                    className="opacity-0 group-hover:opacity-100 text-gray-700 hover:text-gray-400 h-6 w-6"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
