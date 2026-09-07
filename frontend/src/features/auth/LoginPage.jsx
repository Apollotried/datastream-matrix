import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuthTokenCreate } from '../../api/generated/datastream-matrix'
import { useAuth } from '../../auth/useAuth.js'

function getErrorMessage(error) {
  return error?.body?.error?.message ?? error?.message ?? 'Login failed'
}

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [email, setEmail] = useState('mar@mar.com')
  const [password, setPassword] = useState('admin')

  const loginMutation = useAuthTokenCreate({
    mutation: {
      onSuccess: (response) => {
        login({
          access: response.data.access,
          refresh: response.data.refresh,
        })
        navigate('/datasets')
      },
    },
  })

  const handleSubmit = (event) => {
    event.preventDefault()

    loginMutation.mutate({
      data: {
        email,
        password,
      },
    })
  }

  return (
    <main className="page">
      <section className="panel">
        <h1>DataStream Matrix</h1>
        <p>Sign in to manage dataset ingestion jobs.</p>

        <form onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          {loginMutation.isError ? (
            <p role="alert" className="error">
              {getErrorMessage(loginMutation.error)}
            </p>
          ) : null}

          <button type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}