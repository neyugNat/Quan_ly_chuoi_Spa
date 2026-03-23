import { Fragment, useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

export function BranchesPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [name, setName] = useState('')
  const [address, setAddress] = useState('')
  const [status, setStatus] = useState('active')
  const [workingHoursJson, setWorkingHoursJson] = useState('')

  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editAddress, setEditAddress] = useState('')
  const [editStatus, setEditStatus] = useState('active')
  const [editWorkingHoursJson, setEditWorkingHoursJson] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch('/api/branches')
      setItems(data?.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function createBranch(e) {
    e.preventDefault()
    setError('')
    try {
      await apiFetch('/api/branches', {
        method: 'POST',
        body: JSON.stringify({
          name,
          address: address || undefined,
          status,
          working_hours_json: workingHoursJson || undefined,
        }),
      })
      setName('')
      setAddress('')
      setStatus('active')
      setWorkingHoursJson('')
      await load()
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    }
  }

  function startEdit(item) {
    if (!item) return
    setEditingId(item.id)
    setEditName(item.name || '')
    setEditAddress(item.address || '')
    setEditStatus(item.status || 'active')
    setEditWorkingHoursJson(item.working_hours_json || '')
  }

  function cancelEdit() {
    setEditingId(null)
  }

  async function saveEdit(e) {
    e.preventDefault()
    if (!editingId) return
    setError('')
    try {
      await apiFetch(`/api/branches/${editingId}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editName,
          address: editAddress || null,
          status: editStatus,
          working_hours_json: editWorkingHoursJson || null,
        }),
      })
      setEditingId(null)
      await load()
    } catch (err) {
      setError(err?.data?.error || 'update_failed')
    }
  }

  return (
    <div className="panel">
      <div className="page-head">
        <h2 style={{ margin: 0 }}>Chi nhánh</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      {error ? <div className="error">{error}</div> : null}

      <form onSubmit={createBranch} style={{ marginTop: 12 }}>
        <div className="filters" style={{ marginBottom: 0, alignItems: 'flex-end' }}>
          <div className="field" style={{ minWidth: 220 }}>
            <label>Tên</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="field" style={{ minWidth: 240 }}>
            <label>Địa chỉ</label>
            <input value={address} onChange={(e) => setAddress(e.target.value)} />
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label>Status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="active">active</option>
              <option value="inactive">inactive</option>
            </select>
          </div>
          <button className="btn" type="submit">
            Thêm
          </button>
        </div>
        <div className="field" style={{ marginTop: 8 }}>
          <label>Giờ làm việc (JSON)</label>
          <textarea
            value={workingHoursJson}
            onChange={(e) => setWorkingHoursJson(e.target.value)}
            rows={2}
            placeholder='{"mon":"09:00-18:00"}'
          />
        </div>
      </form>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên</th>
              <th>Status</th>
              <th>Địa chỉ</th>
              <th>Tác vụ</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <Fragment key={it.id}>
                <tr onClick={() => startEdit(it)} style={{ cursor: 'pointer' }}>
                  <td>{it.id}</td>
                  <td>{it.name}</td>
                  <td>
                    {it.status === 'active' ? (
                      <span className="badge success">Hoạt động</span>
                    ) : it.status === 'inactive' ? (
                      <span className="badge warning">Ngừng</span>
                    ) : (
                      it.status
                    )}
                  </td>
                  <td>{it.address || ''}</td>
                  <td>
                    <button
                      className="btn btn-sm"
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        startEdit(it)
                      }}
                    >
                      Sửa
                    </button>
                  </td>
                </tr>
                {editingId === it.id ? (
                  <tr>
                    <td colSpan={5}>
                      <form onSubmit={saveEdit}>
                        <div className="filters" style={{ marginBottom: 0, alignItems: 'flex-end' }}>
                          <div className="field" style={{ minWidth: 220 }}>
                            <label>Tên</label>
                            <input value={editName} onChange={(e) => setEditName(e.target.value)} required />
                          </div>
                          <div className="field" style={{ minWidth: 240 }}>
                            <label>Địa chỉ</label>
                            <input value={editAddress} onChange={(e) => setEditAddress(e.target.value)} />
                          </div>
                          <div className="field" style={{ minWidth: 160 }}>
                            <label>Status</label>
                            <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                              <option value="active">active</option>
                              <option value="inactive">inactive</option>
                            </select>
                          </div>
                          <button className="btn btn-sm" type="submit">
                            Lưu
                          </button>
                          <button className="btn btn-sm btn-ghost" type="button" onClick={cancelEdit}>
                            Hủy
                          </button>
                        </div>
                        <div className="field" style={{ marginTop: 8 }}>
                          <label>Giờ làm việc (JSON)</label>
                          <textarea
                            value={editWorkingHoursJson}
                            onChange={(e) => setEditWorkingHoursJson(e.target.value)}
                            rows={2}
                          />
                        </div>
                      </form>
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            ))}
            {items.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ color: 'var(--muted)' }}>
                  Không có dữ liệu
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
