import { getToken, removeToken } from './authStorage'

const API_URL = import.meta.env.VITE_API_URL || ''

export async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {})
  headers.set('Content-Type', 'application/json')

  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const branchId = localStorage.getItem('branch_id')
  if (branchId) headers.set('X-Branch-Id', branchId)

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  if (res.status === 401) {
    removeToken()
  }

  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    const err = new Error('api_error')
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}
