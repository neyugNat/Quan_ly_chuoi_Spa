import { Fragment, useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

export function ResourcesPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [name, setName] = useState('')
  const [resourceType, setResourceType] = useState('room')
  const [code, setCode] = useState('')
  const [status, setStatus] = useState('active')
  const [maintenanceFlag, setMaintenanceFlag] = useState(false)
  const [note, setNote] = useState('')

  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editResourceType, setEditResourceType] = useState('')
  const [editCode, setEditCode] = useState('')
  const [editStatus, setEditStatus] = useState('active')
  const [editMaintenanceFlag, setEditMaintenanceFlag] = useState(false)
  const [editNote, setEditNote] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch('/api/resources')
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

  async function createResource(e) {
    e.preventDefault()
    setError('')
    try {
      await apiFetch('/api/resources', {
        method: 'POST',
        body: JSON.stringify({
          name,
          resource_type: resourceType,
          code: code || undefined,
          status,
          maintenance_flag: maintenanceFlag,
          note: note || undefined,
        }),
      })
      setName('')
      setResourceType('room')
      setCode('')
      setStatus('active')
      setMaintenanceFlag(false)
      setNote('')
      await load()
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    }
  }

  function startEdit(item) {
    if (!item) return
    setEditingId(item.id)
    setEditName(item.name || '')
    setEditResourceType(item.resource_type || '')
    setEditCode(item.code || '')
    setEditStatus(item.status || 'active')
    setEditMaintenanceFlag(!!item.maintenance_flag)
    setEditNote(item.note || '')
  }

  function cancelEdit() {
    setEditingId(null)
  }

  async function saveEdit(e) {
    e.preventDefault()
    if (!editingId) return
    setError('')
    try {
      await apiFetch(`/api/resources/${editingId}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editName,
          resource_type: editResourceType,
          status: editStatus,
          code: editCode || null,
          maintenance_flag: !!editMaintenanceFlag,
          note: editNote || null,
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
        <h2 style={{ margin: 0 }}>Tài nguyên</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      {error ? <div className="error">{error}</div> : null}

      <form onSubmit={createResource} style={{ marginTop: 12 }}>
        <div className="filters" style={{ marginBottom: 0 }}>
          <div className="field" style={{ minWidth: 220 }}>
            <label>Tên</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label>Loại</label>
            <input value={resourceType} onChange={(e) => setResourceType(e.target.value)} required />
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label>Mã</label>
            <input value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label>Status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="active">active</option>
              <option value="inactive">inactive</option>
            </select>
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label>Maintenance</label>
            <input
              type="checkbox"
              checked={maintenanceFlag}
              onChange={(e) => setMaintenanceFlag(e.target.checked)}
            />
          </div>
          <button className="btn btn-sm" type="submit">
            Thêm
          </button>
        </div>
        <div className="field" style={{ marginTop: 8 }}>
          <label>Ghi chú</label>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} />
        </div>
      </form>

      <div className="table-wrap" style={{ marginTop: 14 }}>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên</th>
              <th>Loại</th>
              <th>Mã</th>
              <th>Status</th>
              <th>Maintenance</th>
              <th>Tác vụ</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <Fragment key={it.id}>
                <tr onClick={() => startEdit(it)} style={{ cursor: 'pointer' }}>
                  <td>{it.id}</td>
                  <td>{it.name}</td>
                  <td>{it.resource_type}</td>
                  <td>{it.code || ''}</td>
                  <td>
                    {it.status === 'active' ? (
                      <span className="badge success">Hoạt động</span>
                    ) : it.status === 'inactive' ? (
                      <span className="badge warning">Ngừng</span>
                    ) : (
                      it.status
                    )}
                  </td>
                  <td>
                    {it.maintenance_flag ? (
                      <span className="badge danger">Bảo trì</span>
                    ) : (
                      <span className="badge success">Sẵn sàng</span>
                    )}
                  </td>
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
                    <td colSpan={7}>
                      <form onSubmit={saveEdit}>
                        <div className="filters" style={{ marginBottom: 0 }}>
                          <div className="field" style={{ minWidth: 220 }}>
                            <label>Tên</label>
                            <input value={editName} onChange={(e) => setEditName(e.target.value)} required />
                          </div>
                          <div className="field" style={{ minWidth: 160 }}>
                            <label>Loại</label>
                            <input
                              value={editResourceType}
                              onChange={(e) => setEditResourceType(e.target.value)}
                              required
                            />
                          </div>
                          <div className="field" style={{ minWidth: 160 }}>
                            <label>Mã</label>
                            <input value={editCode} onChange={(e) => setEditCode(e.target.value)} />
                          </div>
                          <div className="field" style={{ minWidth: 160 }}>
                            <label>Status</label>
                            <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                              <option value="active">active</option>
                              <option value="inactive">inactive</option>
                            </select>
                          </div>
                          <div className="field" style={{ minWidth: 160 }}>
                            <label>Maintenance</label>
                            <input
                              type="checkbox"
                              checked={editMaintenanceFlag}
                              onChange={(e) => setEditMaintenanceFlag(e.target.checked)}
                            />
                          </div>
                          <button className="btn btn-sm" type="submit">
                            Lưu
                          </button>
                          <button className="btn btn-sm btn-ghost" type="button" onClick={cancelEdit}>
                            Hủy
                          </button>
                        </div>
                        <div className="field" style={{ marginTop: 8 }}>
                          <label>Ghi chú</label>
                          <textarea value={editNote} onChange={(e) => setEditNote(e.target.value)} rows={2} />
                        </div>
                      </form>
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            ))}
            {items.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ color: 'var(--muted)' }}>
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
