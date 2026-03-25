'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import api from '@/services/api'

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/dashboard/customers': 'Customer Management',
  '/dashboard/kyc': 'KYC Management',
  '/dashboard/cards': 'Card Management',
  '/dashboard/transactions': 'Transactions',
  '/dashboard/security': 'Security Center',
  '/dashboard/audit': 'Audit Logs',
  '/dashboard/settings': 'Settings',
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState<{ name: string; email: string } | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    const storedUser = localStorage.getItem('user')

    if (!token) {
      router.push('/')
      return
    }

    api.setToken(token)

    if (storedUser) {
      setUser(JSON.parse(storedUser))
    }
  }, [router])

  const handleLogout = async () => {
    await api.logout()
    api.clearToken()
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
    localStorage.removeItem('refresh_token')
    router.push('/')
  }

  const title = pageTitles[pathname] || 'Dashboard'

  return (
    <div className="flex h-screen">
      <Sidebar onLogout={handleLogout} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title={title} user={user || undefined} />
        <main className="flex-1 overflow-y-auto bg-muted/30 p-6">{children}</main>
      </div>
    </div>
  )
}
