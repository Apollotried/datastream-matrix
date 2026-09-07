import { createContext, useEffect, useMemo, useState } from 'react'

import { AUTH_EXPIRED_EVENT } from '../api/mutator'

export const AuthContext = createContext(null)

const ACCESS_TOKEN_KEY = 'accessToken'
const REFRESH_TOKEN_KEY = 'refreshToken'

function readStoredToken(key) {
  return window.localStorage.getItem(key)
}

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() =>
    readStoredToken(ACCESS_TOKEN_KEY),
  )

  useEffect(() => {
    const handleAuthExpired = () => {
      setAccessToken(null)
    }

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired)

    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired)
    }
  }, [])

  const login = ({ access, refresh }) => {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, access)
    window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
    setAccessToken(access)
  }

  const logout = () => {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY)
    window.localStorage.removeItem(REFRESH_TOKEN_KEY)
    setAccessToken(null)
  }

  const value = useMemo(
    () => ({
      accessToken,
      isAuthenticated: Boolean(accessToken),
      login,
      logout,
    }),
    [accessToken],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
