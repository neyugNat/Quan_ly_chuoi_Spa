import { Fragment, useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

function parseOptionalInt(value) {
  const text = String(value || '').trim()
  if (!text) return null
  return Number.parseInt(text, 10)
}

export function PackagesPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [customers, setCustomers] = useState([])
  const [sellCustomerId, setSellCustomerId] = useState('')
  const [sellPackageId, setSellPackageId] = useState('')
  const [selling, setSelling] = useState(false)
  const [sellError, setSellError] = useState('')
  const [soldCustomerPackages, setSoldCustomerPackages] = useState([])

  const [name, setName] = useState('')
  const [sessionsTotal, setSessionsTotal] = useState('')
  const [validityDays, setValidityDays] = useState('')
  const [shareable, setShareable] = useState(false)
  const [status, setStatus] = useState('active')

  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editSessionsTotal, setEditSessionsTotal] = useState('')
  const [editValidityDays, setEditValidityDays] = useState('')
  const [editShareable, setEditShareable] = useState(false)
  const [editStatus, setEditStatus] = useState('active')
  const [updating, setUpdating] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [packagesData, customersData] = await Promise.all([
        apiFetch('/api/packages'),
        apiFetch('/api/customers'),
      ])
      setItems(packagesData.items || [])
      setCustomers(customersData.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const loadCustomerPackages = useCallback(async (customerId) => {
    if (!customerId) {
      setSoldCustomerPackages([])
      return
    }
    try {
      const data = await apiFetch(`/api/customer-packages?customer_id=${encodeURIComponent(customerId)}`)
      setSoldCustomerPackages(data?.items || [])
    } catch {
      setSoldCustomerPackages([])
    }
  }, [])

  useEffect(() => {
    loadCustomerPackages(sellCustomerId)
  }, [sellCustomerId, loadCustomerPackages])

  async function sellPackage(e) {
    e.preventDefault()
    setSellError('')
    if (!sellCustomerId || !sellPackageId) return
    setSelling(true)
    try {
      await apiFetch('/api/customer-packages', {
        method: 'POST',
        body: JSON.stringify({
          customer_id: Number.parseInt(sellCustomerId, 10),
          package_id: Number.parseInt(sellPackageId, 10),
        }),
      })
      await loadCustomerPackages(sellCustomerId)
    } catch (err) {
      setSellError(err?.data?.error || 'sell_failed')
    } finally {
      setSelling(false)
    }
  }

  async function createPackage(e) {
    e.preventDefault()
    setError('')
    try {
      const payload = {
        name,
        sessions_total: Number.parseInt(sessionsTotal, 10),
      }
      const parsedValidityDays = parseOptionalInt(validityDays)
      if (parsedValidityDays !== null) payload.validity_days = parsedValidityDays
      payload.shareable = shareable
      if (status) payload.status = status

      await apiFetch('/api/packages', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setName('')
      setSessionsTotal('')
      setValidityDays('')
      setShareable(false)
      setStatus('active')
      await load()
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    }
  }

  function startEdit(pkg) {
    setEditingId(pkg.id)
    setEditName(pkg.name || '')
    setEditSessionsTotal(String(pkg.sessions_total ?? ''))
    setEditValidityDays(String(pkg.validity_days ?? ''))
    setEditShareable(Boolean(pkg.shareable))
    setEditStatus(pkg.status || 'active')
  }

  function cancelEdit() {
    setEditingId(null)
    setEditName('')
    setEditSessionsTotal('')
    setEditValidityDays('')
    setEditShareable(false)
    setEditStatus('active')
  }

  async function updatePackage(e) {
    e.preventDefault()
    if (!editingId) return
    setError('')
    setUpdating(true)
    try {
      await apiFetch(`/api/packages/${editingId}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editName,
          sessions_total: Number.parseInt(editSessionsTotal, 10),
          validity_days: parseOptionalInt(editValidityDays),
          shareable: editShareable,
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
        <h2 style={{ margin: 0 }}>Gói liệu trình</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      <form onSubmit={createPackage} style={{ marginTop: 12 }}>
        <div className="filters" style={{ marginBottom: 0 }}>
          <input placeholder="Tên gói" value={name} onChange={(e) => setName(e.target.value)} required />
          <input
            placeholder="Tổng số buổi"
            type="number"
            value={sessionsTotal}
            onChange={(e) => setSessionsTotal(e.target.value)}
            required
          />
          <input
            placeholder="Hiệu lực (ngày)"
            type="number"
            value={validityDays}
            onChange={(e) => setValidityDays(e.target.value)}
          />
          <label className="row" style={{ gap: 6 }}>
            <input type="checkbox" checked={shareable} onChange={(e) => setShareable(e.target.checked)} />
            Shareable
          </label>
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

      <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
        <h3 style={{ margin: '0 0 8px 0' }}>Bán gói cho khách</h3>
        <form onSubmit={sellPackage}>
          <div className="filters" style={{ marginBottom: 0 }}>
            <select value={sellCustomerId} onChange={(e) => setSellCustomerId(e.target.value)} required>
              <option value="">Chọn khách hàng *</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_name} ({c.phone})
                </option>
              ))}
            </select>

            <select value={sellPackageId} onChange={(e) => setSellPackageId(e.target.value)} required>
              <option value="">Chọn gói *</option>
              {items.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} (#{p.id})
                </option>
              ))}
            </select>

            <button className="btn btn-sm" type="submit" disabled={selling}>
              {selling ? 'Đang tạo...' : 'Bán gói'}
            </button>
          </div>
        </form>
        {sellError ? <div className="error">{sellError}</div> : null}

        {sellCustomerId ? (
          <div className="table-wrap" style={{ marginTop: 10 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>package_id</th>
                  <th>Tổng</th>
                  <th>Còn lại</th>
                  <th>Hết hạn</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {soldCustomerPackages.map((cp) => (
                  <tr key={cp.id}>
                    <td>{cp.id}</td>
                    <td>{cp.package_id}</td>
                    <td>{cp.sessions_total}</td>
                    <td>{cp.sessions_remaining}</td>
                    <td>{cp.expires_at ? String(cp.expires_at).slice(0, 10) : '-'}</td>
                    <td>
                      {cp.status === 'active' ? (
                        <span className="badge success">Hoạt động</span>
                      ) : cp.status === 'inactive' ? (
                        <span className="badge warning">Ngừng</span>
                      ) : (
                        cp.status
                      )}
                    </td>
                  </tr>
                ))}
                {soldCustomerPackages.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ padding: 10, color: 'var(--muted)' }}>
                      Khách chưa có gói
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <div className="table-wrap" style={{ marginTop: 14 }}>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên</th>
              <th>Tổng buổi</th>
              <th>Số buổi còn lại</th>
              <th>Hiệu lực</th>
              <th>Shareable</th>
              <th>Status</th>
              <th>Tác vụ</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <Fragment key={p.id}>
                <tr onClick={() => startEdit(p)} style={{ cursor: 'pointer' }}>
                  <td>{p.id}</td>
                  <td>{p.name}</td>
                  <td>{p.sessions_total}</td>
                  <td>-</td>
                  <td>{p.validity_days || '-'}</td>
                  <td>{p.shareable ? 'yes' : 'no'}</td>
                  <td>
                    {p.status === 'active' ? (
                      <span className="badge success">Hoạt động</span>
                    ) : p.status === 'inactive' ? (
                      <span className="badge warning">Ngừng</span>
                    ) : (
                      p.status
                    )}
                  </td>
                  <td>
                    <button
                      className="btn btn-sm"
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        startEdit(p)
                      }}
                    >
                      Sửa
                    </button>
                  </td>
                </tr>
                {editingId === p.id ? (
                  <tr>
                    <td colSpan={8}>
                      <form onSubmit={updatePackage}>
                        <div className="filters" style={{ marginBottom: 0 }}>
                          <input
                            placeholder="Tên gói"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            required
                          />
                          <input
                            placeholder="Tổng số buổi"
                            type="number"
                            value={editSessionsTotal}
                            onChange={(e) => setEditSessionsTotal(e.target.value)}
                            required
                          />
                          <input
                            placeholder="Hiệu lực (ngày)"
                            type="number"
                            value={editValidityDays}
                            onChange={(e) => setEditValidityDays(e.target.value)}
                          />
                          <label className="row" style={{ gap: 6 }}>
                            <input
                              type="checkbox"
                              checked={editShareable}
                              onChange={(e) => setEditShareable(e.target.checked)}
                            />
                            Shareable
                          </label>
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
                <td colSpan={8} style={{ padding: 10, color: 'var(--muted)' }}>
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
