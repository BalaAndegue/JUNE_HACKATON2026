'use client'

import { useState } from 'react'
import { useAuthStore } from '@/store/auth.store'
import { authService } from '@/services/auth.service'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { toast } from 'sonner'

export default function SettingsPage() {
  const { user, setUser } = useAuthStore()
  const [name, setName] = useState(user?.name ?? '')
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url ?? '')
  const [isSaving, setIsSaving] = useState(false)
  const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' })
  const [isChangingPwd, setIsChangingPwd] = useState(false)

  const initials = name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)

  const handleSaveProfile = async () => {
    setIsSaving(true)
    try {
      const updated = await authService.updateProfile({ name, avatar_url: avatarUrl || undefined })
      setUser({ ...user!, ...updated })
      toast.success('Profil mis à jour')
    } catch { toast.error('Erreur') }
    finally { setIsSaving(false) }
  }

  const handleChangePassword = async () => {
    if (passwords.new !== passwords.confirm) {
      toast.error('Les mots de passe ne correspondent pas')
      return
    }
    if (passwords.new.length < 8) {
      toast.error('Min. 8 caractères')
      return
    }
    setIsChangingPwd(true)
    try {
      await authService.changePassword({ current_password: passwords.current, new_password: passwords.new })
      setPasswords({ current: '', new: '', confirm: '' })
      toast.success('Mot de passe modifié. Toutes les sessions ont été révoquées.')
    } catch { toast.error('Mot de passe actuel incorrect') }
    finally { setIsChangingPwd(false) }
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-xl font-bold text-gray-100">Paramètres</h1>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profil</CardTitle>
          <CardDescription>Gérez vos informations personnelles</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarImage src={avatarUrl} />
              <AvatarFallback className="text-lg">{initials}</AvatarFallback>
            </Avatar>
            <div className="flex-1 space-y-1.5">
              <Label htmlFor="avatar">URL de l'avatar</Label>
              <Input id="avatar" placeholder="https://…" value={avatarUrl} onChange={(e) => setAvatarUrl(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="name">Nom complet</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Email</Label>
            <Input value={user?.email ?? ''} disabled className="opacity-50" />
          </div>
          <Button onClick={handleSaveProfile} disabled={isSaving}>
            {isSaving ? 'Sauvegarde…' : 'Sauvegarder'}
          </Button>
        </CardContent>
      </Card>

      {/* Password */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Mot de passe</CardTitle>
          <CardDescription>Changer votre mot de passe révoquera toutes vos sessions actives</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>Mot de passe actuel</Label>
            <Input type="password" value={passwords.current} onChange={(e) => setPasswords({ ...passwords, current: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label>Nouveau mot de passe</Label>
            <Input type="password" value={passwords.new} onChange={(e) => setPasswords({ ...passwords, new: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label>Confirmer</Label>
            <Input type="password" value={passwords.confirm} onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })} />
          </div>
          <Button onClick={handleChangePassword} disabled={isChangingPwd}>
            {isChangingPwd ? 'Modification…' : 'Changer le mot de passe'}
          </Button>
        </CardContent>
      </Card>

      {/* Danger zone */}
      <Card className="border-red-500/20">
        <CardHeader>
          <CardTitle className="text-base text-red-400">Zone de danger</CardTitle>
          <CardDescription>Actions irréversibles</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm font-medium text-gray-300">Supprimer mon compte</p>
              <p className="text-xs text-gray-600">Toutes vos données seront supprimées définitivement</p>
            </div>
            <Button variant="destructive" size="sm">Supprimer</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
