import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/api'
import { getToken, removeToken, setToken } from '../lib/authStorage'

const AuthContext = createContext(null)

function normalizeBranchIds(user) {
  const ids = user?.branch_ids
  if (!Array.isArray(ids)) return []
  return ids.map((v) => String(v)).filter(Boolean)
}

function ensureBranchIdForUser(user) {
  const allowed = normalizeBranchIds(user)
  if (allowed.length === 0) return

  const current = localStorage.getItem('branch_id')
  if (allowed.length === 1) {
    const only = allowed[0]
    if (current !== only) localStorage.setItem('branch_id', only)
    return
  }

  if (!current || !allowed.includes(String(current))) {
    localStorage.setItem('branch_id', allowed[0])
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [booted, setBooted] = useState(false)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setBooted(true)
      return
    }
    apiFetch('/api/auth/me')
      .then((u) => {
        ensureBranchIdForUser(u)
        setUser(u)
      })
      .catch(() => removeToken())
      .finally(() => setBooted(true))
  }, [])

  async function login(username, password) {
    const result = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    setToken(result.token)
    ensureBranchIdForUser(result.user)
    setUser(result.user)
  }

  function logout() {
    removeToken()
    localStorage.removeItem('branch_id')
    setUser(null)
  }

  const value = useMemo(
    () => ({
      booted,
      user,
      isAuthenticated: !!user,
      login,
      logout,
      setToken,
    }),
    [booted, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('AuthContext missing')
  return ctx
}
