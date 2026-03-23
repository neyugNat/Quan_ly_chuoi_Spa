import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'

export function ProtectedRoute({ allowedRoles }) {
  const { booted, isAuthenticated, user } = useAuth()
  const location = useLocation()

  if (!booted) return null
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (allowedRoles && user) {
    const roles = user.roles || []
    const ok = roles.some((r) => allowedRoles.includes(r))
    if (!ok) return <Navigate to="/unauthorized" replace />
  }

  return <Outlet />
}
