# -*- coding: utf-8 -*-
content = """import { Fragment, useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

export function UsersPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [createRoleNames, setCreateRoleNames] = useState([])
  const [createBranchIds, setCreateBranchIds] = useState([])
  const [createIsActive, setCreateIsActive] = useState(true)

  const [roles, setRoles] = useState([])
  const [branches, setBranches] = useState([])

  const [editingId, setEditingId] = useState(null)
  const [editUsername, setEditUsername] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [editRoleNames, setEditRoleNames] = useState([])
  const [editBranchIds, setEditBranchIds] = useState([])
  const [editIsActive, setEditIsActive] = useState(true)

  const [editingPasswordId, setEditingPasswordId] = useState(null)
  const [newPassword, setNewPassword] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const query = searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : ''
      const data = await apiFetch(`/api/users${query}`)
      setItems(data?.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [searchQuery])

  const loadRoles = useCallback(async () => {
    try {
      const data = await apiFetch('/api/roles')
      setRoles(data?.items || data || [])
    } catch (err) {
      console.error('load_roles_failed', err)
    }
  }, [])

  const loadBranches = useCallback(async () => {
    try {
      const data = await apiFetch('/api/branches')
      setBranches(data?.items || [])
    } catch (err) {
      console.error('load_branches_failed', err)
    }
  }, [])

  useEffect(() => {
    load()
    loadRoles()
    loadBranches()
  }, [load, loadRoles, loadBranches])

  async function createUser(e) {
    e.preventDefault()
    setError('')
    try {
      await apiFetch('/api/users', {
        method: 'POST',
        body: JSON.stringify({
          username,
          email: email || undefined,
          password,
          role_names: createRoleNames,
          branch_ids: createBranchIds,
          is_active: createIsActive,
        }),
      })
      setUsername('')
      setEmail('')
      setPassword('')
      setCreateRoleNames([])
      setCreateBranchIds([])
      setCreateIsActive(true)
      await load()
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    }
  }

  function startEdit(item) {
    if (!item) return
    setEditingId(item.id)
    setEditUsername(item.username || '')
    setEditEmail(item.email || '')
    setEditRoleNames(item.role_names || [])
    setEditBranchIds(item.branch_ids || [])
    setEditIsActive(item.is_active !== false)
  }

  function cancelEdit() {
    setEditingId(null)
  }

  async function saveEdit(e) {
    e.preventDefault()
    if (!editingId) return
    setError('')
    try {
      await apiFetch(`/api/users/${editingId}`, {
        method: 'PUT',
        body: JSON.stringify({
          username: editUsername,
          email: editEmail || null,
          role_names: editRoleNames,
          branch_ids: editBranchIds,
          is_active: editIsActive,
        }),
      })
      setEditingId(null)
      await load()
    } catch (err) {
      setError(err?.data?.error || 'update_failed')
    }
  }

  async function deleteUser(id) {
    if (!window.confirm('Bạn có chắc muốn xóa tài khoản này?')) return
    setError('')
    try {
      await apiFetch(`/api/users/${id}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err?.data?.error || 'delete_failed')
    }
  }

  function startSetPassword(id) {
    setEditingPasswordId(id)
    setNewPassword('')
  }

  function cancelSetPassword() {
    setEditingPasswordId(null)
    setNewPassword('')
  }

  async function saveSetPassword(e) {
    e.preventDefault()
    if (!editingPasswordId) return
    setError('')
    try {
      await apiFetch(`/api/users/${editingPasswordId}/set-password`, {
        method: 'POST',
        body: JSON.stringify({ new_password: newPassword }),
      })
      setEditingPasswordId(null)
      setNewPassword('')
    } catch (err) {
      setError(err?.data?.error || 'set_password_failed')
    }
  }

  function toggleRole(arr, val, setter) {
    if (arr.includes(val)) {
      setter(arr.filter((v) => v !== val))
    } else {
      setter([...arr, val])
    }
  }

  function toggleBranch(arr, val, setter) {
    if (arr.includes(val)) {
      setter(arr.filter((v) => v !== val))
    } else {
      setter([...arr, val])
    }
  }

  return (
    <div className="panel">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>Tài khoản</h2>
        <div className="row" style={{ gap: 8 }}>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm..."
            style={{ minWidth: 200 }}
          />
          <button className="btn" type="button" onClick={load} disabled={loading}>
            Tải lại
          </button>
        </div>
      </div>

      {error ? <div className="error">{error}</div> : null}

      <form onSubmit={createUser} style={{ marginTop: 12 }}>
        <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div className="field" style={{ minWidth: 140 }}>
            <label>Tên đăng nhập</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
          <div className="field" style={{ minWidth: 180 }}>
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field" style={{ minWidth: 140 }}>
            <label>Mật khẩu</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <div className="field" style={{ minWidth: 120 }}>
            <label>Kích hoạt</label>
            <select value={createIsActive ? 'true' : 'false'} onChange={(e) => setCreateIsActive(e.target.value === 'true')}>
              <option value="true">Có</option>
              <option value="false">Không</option>
            </select>
          </div>
          <button className="btn" type="submit">
            Thêm
          </button>
        </div>
        <div className="row" style={{ gap: 16, marginTop: 8, flexWrap: 'wrap' }}>
          <div className="field" style={{ flex: 1, minWidth: 200 }}>
            <label>Vai trò</label>
            <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
              {roles.map((r) => (
                <label key={r.name} style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={createRoleNames.includes(r.name)}
                    onChange={() => toggleRole(createRoleNames, r.name, setCreateRoleNames)}
                  />
                  {r.name}
                </label>
              ))}
            </div>
          </div>
          <div className="field" style={{ flex: 1, minWidth: 200 }}>
            <label>Chi nhánh</label>
            <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
              {branches.map((b) => (
                <label key={b.id} style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={createBranchIds.includes(b.id)}
                    onChange={() => toggleBranch(createBranchIds, b.id, setCreateBranchIds)}
    
