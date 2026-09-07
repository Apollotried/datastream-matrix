import { Navigate } from 'react-router-dom'

import { useAuth } from '../auth/useAuth.js'

export function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

export function GuestRoute({ children }) {
  const { isAuthenticated } = useAuth()

  if (isAuthenticated) {
    return <Navigate to="/datasets" replace />
  }

  return children
}