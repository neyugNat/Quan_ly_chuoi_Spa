import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/', { replace: true })
    } catch (err) {
      const msg = err?.data?.error || 'login_failed'
      setError(String(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login">
      <div className="panel login-card">
        <h2 style={{ margin: 0 }}>Đăng nhập</h2>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button className="btn" disabled={loading} type="submit">
            {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>
          {error ? <div className="error">{error}</div> : null}
        </form>
      </div>
    </div>
  )
}
