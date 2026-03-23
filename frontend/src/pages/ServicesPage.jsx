import { Fragment, useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

export function ServicesPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [durationMinutes, setDurationMinutes] = useState('')
  const [status, setStatus] = useState('active')

  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editPrice, setEditPrice] = useState('')
  const [editDurationMinutes, setEditDurationMinutes] = useState('')
  const [editStatus, setEditStatus] = useState('active')
  const [updating, setUpdating] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch('/api/services')
      setItems(data.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function createService(e) {
    e.preventDefault()
    setError('')
    try {
      const payload = {
        name,
        price: Number.parseFloat(price),
        duration_minutes: Number.parseInt(durationMinutes, 10),
      }
      if (status) payload.status = status

      await apiFetch('/api/services', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setName('')
      setPrice('')
      setDurationMinutes('')
      setStatus('active')
      await load()
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    }
  }

  function startEdit(service) {
    setEditingId(service.id)
    setEditName(service.name || '')
    setEditPrice(String(service.price ?? ''))
    setEditDurationMinutes(String(service.duration_minutes ?? ''))
    setEditStatus(service.status || 'active')
  }

  function cancelEdit() {
    setEditingId(null)
    setEditName('')
    setEditPrice('')
    setEditDurationMinutes('')
    setEditStatus('active')
  }

  async function updateService(e) {
    e.preventDefault()
    if (!editingId) return
    setError('')
    setUpdating(true)
    try {
      await apiFetch(`/api/services/${editingId}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editName,
          price: Number.parseFloat(editPrice),
          duration_minutes: Number.parseInt(editDurationMinutes, 10),
          status: editStatus,
        }),
      })
      cancelEdit()
      await load()
    } catch (err) {
      setError(err?.data?.error || 'update_failed')
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="panel">
      <div className="page-head">
        <h2 style={{ margin: 0 }}>Dịch vụ</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      <form onSubmit={createService} style={{ marginTop: 12 }}>
        <div className="filters" style={{ marginBottom: 0 }}>
          <input placeholder="Tên dịch vụ" value={name} onChange={(e) => setName(e.target.value)} required />
          <input
            placeholder="Giá"
            type="number"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            required
          />
          <input
            placeholder="Thời lượng (phút)"
            type="number"
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(e.target.value)}
            required
          />
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="active">active</option>
            <option value="inactive">inactive</option>
          </select>
          <button className="btn btn-sm" type="submit">
            Tạo
          </button>
        </div>
      </form>

      {error ? <div className="error">{error}</div> : null}

      <div className="table-wrap" style={{ marginTop: 14 }}>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên</th>
              <th>Giá</th>
              <th>Thời lượng</th>
              <th>Status</th>
              <th>Tác vụ</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <Fragment key={s.id}>
                <tr onClick={() => startEdit(s)} style={{ cursor: 'pointer' }}>
                  <td>{s.id}</td>
                  <td>{s.name}</td>
                  <td>{s.price}</td>
                  <td>{s.duration_minutes}</td>
                  <td>
                    {s.status === 'active' ? (
                      <span className="badge success">Hoạt động</span>
                    ) : s.status === 'inactive' ? (
                      <span className="badge warning">Ngừng</span>
                    ) : (
                      s.status
                    )}
                  </td>
                  <td>
                    <button
                      className="btn btn-sm"
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        startEdit(s)
                      }}
                    >
                      Sửa
                    </button>
                  </td>
                </tr>
                {editingId === s.id ? (
                  <tr>
                    <td colSpan={6}>
                      <form onSubmit={updateService}>
                        <div className="filters" style={{ marginBottom: 0 }}>
                          <input
                            placeholder="Tên dịch vụ"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            required
                          />
                          <input
                            placeholder="Giá"
                            type="number"
                            step="0.01"
                            value={editPrice}
                            onChange={(e) => setEditPrice(e.target.value)}
                            required
                          />
                          <input
                            placeholder="Thời lượng (phút)"
                            type="number"
                            value={editDurationMinutes}
                            onChange={(e) => setEditDurationMinutes(e.target.value)}
                            required
                          />
                          <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                            <option value="active">active</option>
                            <option value="inactive">inactive</option>
                          </select>
                          <button className="btn btn-sm" type="submit" disabled={updating || loading}>
                            {updating ? 'Đang lưu...' : 'Lưu'}
                          </button>
                          <button className="btn btn-sm btn-ghost" type="button" onClick={cancelEdit} disabled={updating}>
                            Hủy
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
                <td colSpan={6} style={{ color: 'var(--muted)' }}>
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
