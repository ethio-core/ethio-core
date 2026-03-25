'use client'

import { useState, useEffect, useCallback } from 'react'
import api from '@/services/api'

interface User {
  id: string
  email: string
  name: string
  role: string
}

interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  })

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
    if (token) {
      api.setToken(token)
      validateSession()
    } else {
      setState({ user: null, isLoading: false, isAuthenticated: false })
    }
  }, [])

  const validateSession = async () => {
    try {
      const me = await api.getMe()
      if (me.data) {
        const user: User = {
          id: me.data.id,
          email: me.data.email,
          name: me.data.name,
          role: me.data.role,
        }
        localStorage.setItem('user', JSON.stringify(user))
        setState({ user, isLoading: false, isAuthenticated: true })
      } else {
        api.clearToken()
        localStorage.removeItem('user')
        localStorage.removeItem('refresh_token')
        setState({ user: null, isLoading: false, isAuthenticated: false })
      }
    } catch {
      setState({ user: null, isLoading: false, isAuthenticated: false })
    }
  }

  const login = useCallback(async (email: string, password: string) => {
    setState((prev) => ({ ...prev, isLoading: true }))

    const result = await api.login(email, password)

    if (result.data) {
      api.setToken(result.data.access_token)
      localStorage.setItem('refresh_token', result.data.refresh_token)

      const me = await api.getMe()
      if (me.data) {
        const user: User = {
          id: me.data.id,
          email: me.data.email,
          name: me.data.name,
          role: me.data.role,
        }
        localStorage.setItem('user', JSON.stringify(user))
        setState({ user, isLoading: false, isAuthenticated: true })
        return { success: true as const }
      }
    }

    setState((prev) => ({ ...prev, isLoading: false }))
    return { success: false as const, error: result.error }
  }, [])

  const logout = useCallback(async () => {
    await api.logout()
    localStorage.removeItem('user')
    localStorage.removeItem('refresh_token')
    setState({ user: null, isLoading: false, isAuthenticated: false })
  }, [])

  return {
    ...state,
    login,
    logout,
  }
}
