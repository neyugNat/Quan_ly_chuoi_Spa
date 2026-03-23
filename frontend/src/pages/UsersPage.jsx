import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/api'

function toggleString(list, value) {
  const v = String(value)
  if (list.includes(v)) return list.filter((x) => x !== v)
  return [...list, v]
}

function toggleNumber(list, value) {
  const n = Number.parseInt(String(value), 10)
  if (!Number.isFinite(n)) return list
  if (list.includes(n)) return list.filter((x) => x !== n)
  return [...list, n]
}

function normalizeBranchIds(value) {
  return (value || [])
    .map((v) => Number.parseInt(String(v), 10))
    .filter((n) => Number.isFinite(n))
}

export function UsersPage() {
  const [items, setItems] = useState([])
  const [roles, setRoles] = useState([])
  const [branches, setBranches] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [q, setQ] = useState('')

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [roleNames, setRoleNames] = useState([])
  const [branchIds, setBranchIds] = useState([])

  const [editingId, setEditingId] = useState(null)
  const [editUsername, setEditUsername] = useState('')
  const [editIsActive, setEditIsActive] = useState(true)
  const [editRoleNames, setEditRoleNames] = useState([])
  const [editBranchIds, setEditBranchIds] = useState([])
  const [editNewPassword, setEditNewPassword] = useState('')

  const [saving, setSaving] = useState(false)
  const [savingPassword, setSavingPassword] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const branchesById = useMemo(() => {
    const map = new Map()
    for (const b of branches) map.set(Number(b.id), b)
    return map
  }, [branches])

  const loadMeta = useCallback(async () => {
    setError('')
    try {
      const [rolesData, branchesData] = await Promise.all([apiFetch('/api/roles'), apiFetch('/api/branches')])
      setRoles(rolesData?.items || [])
      setBranches(branchesData?.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    }
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const query = (q || '').trim()
      const path = query ? `/api/users?q=${encodeURIComponent(query)}` : '/api/users'
      const data = await apiFetch(path)
      setItems(data?.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [q])

  useEffect(() => {
    loadMeta()
  }, [loadMeta])

  useEffect(() => {
    load()
  }, [load])

  async function createUser(e) {
    e.preventDefault()
    setError('')

    if (!username.trim() || !password) return setError('missing_fields')
    if (!Array.isArray(roleNames) || roleNames.length === 0) return setError('missing_fields')
    if (!Array.isArray(branchIds) || branchIds.length === 0) return setError('missing_fields')

    setSaving(true)
    try {
      await apiFetch('/api/users', {
        method: 'POST',
        body: JSON.stringify({
          username: username.trim(),
          password,
          role_names: roleNames,
          branch_ids: branchIds,
          is_active: !!isActive,
        }),
      })
      setUsername('')
      setPassword('')
      setIsActive(true)
      setRoleNames([])
      setBranchIds([])
      await load()
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    } finally {
      setSaving(false)
    }
  }

  function startEdit(u) {
    if (!u) return
    setEditingId(u.id)
    setEditUsername(u.username || '')
    setEditIsActive(!!u.is_active)
    setEditRoleNames((u.roles || []).map(String))
    setEditBranchIds(normalizeBranchIds(u.branch_ids))
    setEditNewPassword('')
  }

  function cancelEdit() {
    setEditingId(null)
    setEditNewPassword('')
  }

  async function saveEdit(e) {
    e.preventDefault()
    if (!editingId) return
    setError('')

    if (!editUsername.trim()) return setError('missing_fields')
    if (!Array.isArray(editRoleNames) || editRoleNames.length === 0) return setError('missing_fields')
    if (!Array.isArray(editBranchIds) || editBranchIds.length === 0) return setError('missing_fields')

    setSaving(true)
    try {
      await apiFetch(`/api/users/${editingId}`, {
        method: 'PUT',
        body: JSON.stringify({
          username: editUsername.trim(),
          is_active: !!editIsActive,
          role_names: editRoleNames,
          branch_ids: editBranchIds,
        }),
      })
      cancelEdit()
      await load()
    } catch (err) {
      setError(err?.data?.error || 'update_failed')
    } finally {
      setSaving(false)
    }
  }

  async function setUserPassword(e) {
    e.preventDefault()
    if (!editingId) return
    setError('')
    if (!editNewPassword) return setError('missing_fields')

    setSavingPassword(true)
    try {
      await apiFetch(`/api/users/${editingId}/set-password`, {
        method: 'POST',
        body: JSON.stringify({ new_password: editNewPassword }),
      })
      setEditNewPassword('')
    } catch (err) {
      setError(err?.data?.error || 'update_failed')
    } finally {
      setSavingPassword(false)
    }
  }

  async function deleteUser(userId) {
    if (!userId) return
    if (!window.confirm('Xóa tài khoản này?')) return

    setError('')
    setDeleting(true)
    try {
      await apiFetch(`/api/users/${userId}`, { method: 'DELETE' })
      cancelEdit()
      await load()
    } catch (err) {
      setError(err?.data?.error || 'delete_failed')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="panel">
      <div className="page-head">
        <h2 style={{ margin: 0 }}>Tài khoản</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      {error ? <div className="error">{error}</div> : null}

      <div className="filters" style={{ marginTop: 10, alignItems: 'flex-end', gap: 8 }}>
        <div className="field" style={{ minWidth: 260, marginTop: 0 }}>
          <label htmlFor="users-q">Tìm kiếm (tên đăng nhập)</label>
          <input id="users-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ví dụ: admin" />
        </div>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tìm
        </button>
      </div>

      <form onSubmit={createUser} style={{ marginTop: 12 }}>
        <div className="filters" style={{ gap: 8, alignItems: 'flex-end', marginBottom: 0 }}>
          <div className="field" style={{ minWidth: 220, marginTop: 0 }}>
            <label htmlFor="create-username">Tên đăng nhập</label>
            <input id="create-username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
          <div className="field" style={{ minWidth: 220, marginTop: 0 }}>
            <label htmlFor="create-password">Mật khẩu</label>
            <input
              id="create-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="field" style={{ minWidth: 180, marginTop: 0 }}>
            <label>Hoạt động</label>
            <input type="checkbox" checked={!!isActive} onChange={(e) => setIsActive(e.target.checked)} />
          </div>
          <button className="btn btn-sm" type="submit" disabled={saving}>
            {saving ? 'Đang lưu...' : 'Thêm'}
          </button>
        </div>

        <div className="row" style={{ gap: 16, flexWrap: 'wrap', marginTop: 8, alignItems: 'flex-start' }}>
          <div style={{ minWidth: 260 }}>
            <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 4 }}>Vai trò</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {roles.map((r) => (
                <label key={r.id} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input
                    type="checkbox"
                    checked={roleNames.includes(String(r.name))}
                    onChange={() => setRoleNames((prev) => toggleString(prev, r.name))}
                  />
                  <span>{r.name}</span>
                </label>
              ))}
              {roles.length === 0 ? <div style={{ color: 'var(--muted)' }}>Không có dữ liệu</div> : null}
            </div>
          </div>

          <div style={{ minWidth: 260 }}>
            <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 4 }}>Chi nhánh</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {branches.map((b) => (
                <label key={b.id} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input
                    type="checkbox"
                    checked={branchIds.includes(Number(b.id))}
                    onChange={() => setBranchIds((prev) => toggleNumber(prev, b.id))}
                  />
                  <span>
                    {b.name || `Chi nhánh ${b.id}`} (#{b.id})
                  </span>
                </label>
              ))}
              {branches.length === 0 ? <div style={{ color: 'var(--muted)' }}>Không có dữ liệu</div> : null}
            </div>
          </div>
        </div>
      </form>

      <div className="table-wrap" style={{ marginTop: 12 }}>
        <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Tên đăng nhập</th>
            <th>Vai trò</th>
            <th>Chi nhánh</th>
            <th>Hoạt động</th>
            <th>Tác vụ</th>
          </tr>
        </thead>
        <tbody>
          {items.map((u) => (
            <Fragment key={u.id}>
              <tr onClick={() => startEdit(u)} style={{ cursor: 'pointer' }}>
                <td>{u.id}</td>
                <td>{u.username}</td>
                <td>{(u.roles || []).join(', ')}</td>
                <td>
                  {(u.branch_ids || [])
                    .map((id) => {
                      const b = branchesById.get(Number(id))
                      return b ? `${b.name} (#${id})` : `#${id}`
                    })
                    .join(', ')}
                </td>
                <td>
                  {u.is_active ? <span className="badge success">Có</span> : <span className="badge warning">Không</span>}
                </td>
                <td>Sửa</td>
              </tr>

              {editingId === u.id ? (
                <tr>
                  <td colSpan={6}>
                    <form onSubmit={saveEdit}>
                      <div className="filters" style={{ gap: 8, alignItems: 'flex-end', marginBottom: 0 }}>
                        <div className="field" style={{ minWidth: 220, marginTop: 0 }}>
                          <label htmlFor="edit-username">Tên đăng nhập</label>
                          <input id="edit-username" value={editUsername} onChange={(e) => setEditUsername(e.target.value)} required />
                        </div>
                        <div className="field" style={{ minWidth: 180, marginTop: 0 }}>
                          <label>Hoạt động</label>
                          <input
                            type="checkbox"
                            checked={!!editIsActive}
                            onChange={(e) => setEditIsActive(e.target.checked)}
                          />
                        </div>
                        <button className="btn btn-sm" type="submit" disabled={saving || deleting || savingPassword}>
                          {saving ? 'Đang lưu...' : 'Lưu'}
                        </button>
                        <button
                          className="btn btn-sm btn-ghost"
                          type="button"
                          onClick={cancelEdit}
                          disabled={saving || deleting || savingPassword}
                        >
                          Hủy
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          type="button"
                          onClick={() => deleteUser(u.id)}
                          disabled={saving || deleting || savingPassword}
                        >
                          {deleting ? 'Đang xóa...' : 'Xóa'}
                        </button>
                      </div>

                      <div className="row" style={{ gap: 16, flexWrap: 'wrap', marginTop: 8, alignItems: 'flex-start' }}>
                        <div style={{ minWidth: 260 }}>
                          <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 4 }}>Vai trò</div>
                          <div style={{ display: 'grid', gap: 6 }}>
                            {roles.map((r) => (
                              <label key={r.id} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                <input
                                  type="checkbox"
                                  checked={editRoleNames.includes(String(r.name))}
                                  onChange={() => setEditRoleNames((prev) => toggleString(prev, r.name))}
                                />
                                <span>{r.name}</span>
                              </label>
                            ))}
                          </div>
                        </div>

                        <div style={{ minWidth: 260 }}>
                          <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 4 }}>Chi nhánh</div>
                          <div style={{ display: 'grid', gap: 6 }}>
                            {branches.map((b) => (
                              <label key={b.id} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                <input
                                  type="checkbox"
                                  checked={editBranchIds.includes(Number(b.id))}
                                  onChange={() => setEditBranchIds((prev) => toggleNumber(prev, b.id))}
                                />
                                <span>
                                  {b.name || `Chi nhánh ${b.id}`} (#{b.id})
                                </span>
                              </label>
                            ))}
                          </div>
                        </div>
                      </div>
                    </form>

                    <form onSubmit={setUserPassword} style={{ marginTop: 10 }}>
                      <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                        <div className="field" style={{ minWidth: 240 }}>
                          <label htmlFor="edit-new-password">Đặt lại mật khẩu</label>
                          <input
                            id="edit-new-password"
                            type="password"
                            value={editNewPassword}
                            onChange={(e) => setEditNewPassword(e.target.value)}
                            placeholder="Mật khẩu mới"
                          />
                        </div>
                        <button className="btn btn-sm" type="submit" disabled={saving || deleting || savingPassword}>
                          {savingPassword ? 'Đang lưu...' : 'Lưu mật khẩu'}
                        </button>
                      </div>
                    </form>
                  </td>
                </tr>
              ) : null}
            </Fragment>
          ))}
          {items.length === 0 ? (
            <tr>
              <td colSpan={6} style={{ color: 'var(--muted)' }}>Không có dữ liệu</td>
            </tr>
          ) : null}
        </tbody>
        </table>
      </div>
    </div>
  )
}
