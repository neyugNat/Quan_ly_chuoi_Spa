import { Fragment, useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

export function CustomersPage() {
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editFullName, setEditFullName] = useState('')
  const [editPhone, setEditPhone] = useState('')
  const [editStatus, setEditStatus] = useState('active')
  const [updating, setUpdating] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch(`/api/customers${q ? `?q=${encodeURIComponent(q)}` : ''}`)
      setItems(data.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [q])

  useEffect(() => {
    load()
  }, [load])

  async function createCustomer(e) {
    e.preventDefault()
    setError('')
    try {
      await apiFetch('/api/customers', {
        method: 'POST',
        body: JSON.stringify({ full_name: fullName, phone }),
      })
      setFullName('')
      setPhone('')
      await load()
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    }
  }

  function startEdit(customer) {
    setEditingId(customer.id)
    setEditFullName(customer.full_name || '')
    setEditPhone(customer.phone || '')
    setEditStatus(customer.status || 'active')
  }

  function cancelEdit() {
    setEditingId(null)
    setEditFullName('')
    setEditPhone('')
    setEditStatus('active')
  }

  async function updateCustomer(e) {
    e.preventDefault()
    if (!editingId) return
    setError('')
    setUpdating(true)
    try {
      await apiFetch(`/api/customers/${editingId}`, {
        method: 'PUT',
        body: JSON.stringify({
          full_name: editFullName,
          phone: editPhone,
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
        <h2 style={{ margin: 0 }}>Khách hàng</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      <div className="filters" style={{ marginTop: 12, justifyContent: 'space-between' }}>
        <input placeholder="Tìm theo tên/điện thoại/email" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tìm
        </button>
      </div>

      <form onSubmit={createCustomer} style={{ marginTop: 12 }}>
        <div className="filters" style={{ marginBottom: 0 }}>
          <input placeholder="Họ tên" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <input placeholder="Số điện thoại" value={phone} onChange={(e) => setPhone(e.target.value)} />
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
              <th>Họ tên</th>
              <th>Điện thoại</th>
              <th>Trạng thái</th>
              <th>Tác vụ</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <Fragment key={c.id}>
                <tr onClick={() => startEdit(c)} style={{ cursor: 'pointer' }}>
                  <td>{c.id}</td>
                  <td>{c.full_name}</td>
                  <td>{c.phone}</td>
                  <td>
                    {c.status === 'active' ? (
                      <span className="badge success">Hoạt động</span>
                    ) : c.status === 'inactive' ? (
                      <span className="badge warning">Ngừng</span>
                    ) : (
                      c.status
                    )}
                  </td>
                  <td>
                    <button
                      className="btn btn-sm"
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        startEdit(c)
                      }}
                    >
                      Sửa
                    </button>
                  </td>
                </tr>
                {editingId === c.id ? (
                  <tr>
                    <td colSpan={5}>
                      <form onSubmit={updateCustomer}>
                        <div className="filters" style={{ marginBottom: 0 }}>
                          <input value={editFullName} onChange={(e) => setEditFullName(e.target.value)} placeholder="Họ tên" />
                          <input value={editPhone} onChange={(e) => setEditPhone(e.target.value)} placeholder="Số điện thoại" />
                          <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                            <option value="active">Hoạt động</option>
                            <option value="inactive">Ngừng hoạt động</option>
                          </select>
                          <button className="btn btn-sm" type="submit" disabled={updating || loading}>
                            {updating ? 'Đang lưu...' : 'Lưu'}
                          </button>
                          <button
                            className="btn btn-sm btn-ghost"
                            type="button"
                            onClick={cancelEdit}
                            disabled={updating}
                          >
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
                <td colSpan={5} style={{ color: 'var(--muted)' }}>Không có dữ liệu</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
