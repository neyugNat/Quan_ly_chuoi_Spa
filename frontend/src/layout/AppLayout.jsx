import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { canSeeRoles, NAV } from '../auth/navConfig.js'

export function AppLayout() {
  const { user, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const allowedBranchIds = (() => {
    const ids = user?.branch_ids
    if (!Array.isArray(ids)) return []
    return ids.map((v) => String(v)).filter(Boolean)
  })()

  const currentBranchId = (() => {
    const stored = localStorage.getItem('branch_id')
    if (stored && allowedBranchIds.includes(String(stored))) return String(stored)
    return allowedBranchIds[0] || ''
  })()

  function onChangeBranch(e) {
    const next = String(e.target.value || '').trim()
    if (!next) return
    localStorage.setItem('branch_id', next)
    window.location.reload()
  }

  function openSidebar() {
    setSidebarOpen(true)
    document.body.style.overflow = 'hidden'
  }

  function closeSidebar() {
    setSidebarOpen(false)
    document.body.style.overflow = ''
  }

  return (
    <div className="app-shell">
      {/* Mobile header with hamburger */}
      <div className="mobile-header">
        <button
          type="button"
          onClick={openSidebar}
          aria-label="Mở menu"
          aria-expanded={sidebarOpen}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <span className="brand">QuanLySpa</span>
      </div>

      {/* Sidebar overlay */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'visible' : ''}`}
        onClick={closeSidebar}
        aria-hidden="true"
      />

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <span className="brand">QuanLySpa</span>
          <button
            type="button"
            className="sidebar-close"
            onClick={closeSidebar}
            aria-label="Đóng menu"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div style={{ color: 'var(--muted)', fontSize: 14 }}>{user?.username}</div>
        {allowedBranchIds.length > 1 ? (
          <div style={{ marginTop: 8 }}>
            <label htmlFor="branch-switch" style={{ color: 'var(--muted)', fontSize: 12 }}>
              Chi nhánh
            </label>
            <select id="branch-switch" value={currentBranchId} onChange={onChangeBranch} style={{ width: '100%' }}>
              {allowedBranchIds.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </div>
        ) : allowedBranchIds.length === 1 ? (
          <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 8 }}>Chi nhánh: {allowedBranchIds[0]}</div>
        ) : null}
        <nav className="nav" aria-label="main">
          {NAV.filter((i) => canSeeRoles(user?.roles, i.roles)).map((i) => (
            <NavLink key={i.to} to={i.to} end onClick={closeSidebar}>
              {i.label}
            </NavLink>
          ))}
        </nav>
        <button className="btn" type="button" onClick={logout} style={{ marginTop: 'auto' }}>
          Đăng xuất
        </button>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
