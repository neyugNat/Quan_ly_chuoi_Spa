import { Link } from 'react-router-dom'

export function UnauthorizedPage() {
  return (
    <div className="login">
      <div className="panel login-card">
        <h2 style={{ marginTop: 0 }}>Không đủ quyền</h2>
        <p style={{ color: 'var(--muted)' }}>
          Tài khoản của bạn không có quyền truy cập tính năng này.
        </p>
        <div style={{ marginTop: 14 }}>
          <Link className="btn" to="/dashboard">
            Về Tổng quan
          </Link>
        </div>
      </div>
    </div>
  )
}
