import { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

function todayDateValue() {
  return new Date().toISOString().slice(0, 10)
}

export function ReportsPage() {
  const [from, setFrom] = useState(todayDateValue)
  const [to, setTo] = useState(todayDateValue)
  const [tab, setTab] = useState('revenue')

  const [staffId, setStaffId] = useState('')
  const [serviceId, setServiceId] = useState('')
  const [search, setSearch] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [revenueItems, setRevenueItems] = useState([])
  const [appointmentItems, setAppointmentItems] = useState([])
  const [inventoryItems, setInventoryItems] = useState([])
  const [lowStockItems, setLowStockItems] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (from) params.set('from', from)
      if (to) params.set('to', to)
      if (staffId.trim()) params.set('staff_id', staffId.trim())
      if (serviceId.trim()) params.set('service_id', serviceId.trim())
      const query = params.toString()

      const [revenue, appointments, inventory, lowStock] = await Promise.all([
        apiFetch(`/api/reports/revenue${query ? `?${query}` : ''}`),
        apiFetch(`/api/reports/appointments${query ? `?${query}` : ''}`),
        apiFetch('/api/reports/inventory'),
        apiFetch('/api/reports/low-stock'),
      ])

      setRevenueItems(revenue?.items || [])
      setAppointmentItems(appointments?.items || [])
      setInventoryItems(inventory?.items || [])
      setLowStockItems(lowStock?.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [from, to, staffId, serviceId])

  useEffect(() => {
    load()
  }, [load])

  function TabButton({ id, label }) {
    const active = tab === id
    const className = active ? 'btn btn-sm' : 'btn btn-sm btn-ghost'
    return (
      <button
        type="button"
        className={className}
        onClick={() => setTab(id)}
      >
        {label}
      </button>
    )
  }

  function formatMoney(value) {
    const n = Number(value || 0)
    try {
      return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(n)
    } catch {
      return String(n)
    }
  }

  function formatNumber(value) {
    const n = Number(value || 0)
    try {
      return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(n)
    } catch {
      return String(n)
    }
  }

  const q = search.trim().toLowerCase()
  const filteredInventory = q
    ? inventoryItems.filter((it) => {
        const name = String(it?.name || '').toLowerCase()
        const sku = String(it?.sku || '').toLowerCase()
        return name.includes(q) || sku.includes(q)
      })
    : inventoryItems

  return (
    <div className="panel">
      <div className="page-head">
        <h2 style={{ margin: 0 }}>Báo cáo</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      <div className="filters" style={{ marginTop: 12, alignItems: 'flex-end' }}>
        <div className="field" style={{ marginTop: 0 }}>
          <label htmlFor="reports-from">Từ ngày</label>
          <input id="reports-from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </div>
        <div className="field" style={{ marginTop: 0 }}>
          <label htmlFor="reports-to">Đến ngày</label>
          <input id="reports-to" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </div>
        <div className="field" style={{ marginTop: 0 }}>
          <label htmlFor="reports-staff-id">staff_id (tùy chọn)</label>
          <input
            id="reports-staff-id"
            placeholder="Ví dụ: 1"
            value={staffId}
            onChange={(e) => setStaffId(e.target.value)}
            style={{ width: 160 }}
          />
        </div>
        <div className="field" style={{ marginTop: 0 }}>
          <label htmlFor="reports-service-id">service_id (tùy chọn)</label>
          <input
            id="reports-service-id"
            placeholder="Ví dụ: 2"
            value={serviceId}
            onChange={(e) => setServiceId(e.target.value)}
            style={{ width: 160 }}
          />
        </div>
      </div>

      <div className="filters" style={{ marginTop: 10, gap: 8 }}>
        <TabButton id="revenue" label="Doanh thu" />
        <TabButton id="appointments" label="Lịch hẹn" />
        <TabButton id="inventory" label="Tồn kho" />
        <TabButton id="low_stock" label="Cảnh báo" />
      </div>

      {loading ? <div style={{ marginTop: 12, color: 'var(--muted)' }}>Tải dữ liệu...</div> : null}
      {error ? <div className="error">{error}</div> : null}

      {!error ? (
        <div style={{ marginTop: 12, display: 'grid', gap: 12 }}>
          {tab === 'revenue' ? (
            <section className="card" style={{ padding: 12 }}>
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <h3 style={{ margin: 0 }}>Doanh thu</h3>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  Tổng: {formatMoney(revenueItems.reduce((s, it) => s + Number(it?.revenue || 0), 0))} VND
                </div>
              </div>
              <div className="table-wrap" style={{ marginTop: 10 }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Ngày</th>
                      <th style={{ textAlign: 'right' }}>Doanh thu</th>
                      <th style={{ textAlign: 'right' }}>Giao dịch</th>
                      <th style={{ textAlign: 'right' }}>staff_id</th>
                      <th style={{ textAlign: 'right' }}>service_id</th>
                    </tr>
                  </thead>
                  <tbody>
                    {revenueItems.map((it) => (
                      <tr key={`${it.day}-${it.staff_id || 'all'}-${it.service_id || 'all'}`}>
                        <td>{it.day}</td>
                        <td style={{ textAlign: 'right' }}>{formatMoney(it.revenue)}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.payments_count)}</td>
                        <td style={{ textAlign: 'right' }}>{it.staff_id ?? ''}</td>
                        <td style={{ textAlign: 'right' }}>{it.service_id ?? ''}</td>
                      </tr>
                    ))}
                    {revenueItems.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ color: 'var(--muted)' }}>Không có dữ liệu</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {tab === 'appointments' ? (
            <section className="card" style={{ padding: 12 }}>
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <h3 style={{ margin: 0 }}>Lịch hẹn</h3>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  Tổng: {formatNumber(appointmentItems.reduce((s, it) => s + Number(it?.total || 0), 0))}
                </div>
              </div>
              <div className="table-wrap" style={{ marginTop: 10 }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Ngày</th>
                      <th style={{ textAlign: 'right' }}>Tổng</th>
                      <th style={{ textAlign: 'right' }}>Đã đến</th>
                      <th style={{ textAlign: 'right' }}>Hủy</th>
                      <th style={{ textAlign: 'right' }}>Không đến</th>
                    </tr>
                  </thead>
                  <tbody>
                    {appointmentItems.map((it) => (
                      <tr key={it.day}>
                        <td>{it.day}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.total)}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.arrived)}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.cancelled)}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.no_show)}</td>
                      </tr>
                    ))}
                    {appointmentItems.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ color: 'var(--muted)' }}>Không có dữ liệu</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {tab === 'inventory' ? (
            <section className="card" style={{ padding: 12 }}>
              <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Tồn kho</h3>
                  <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 6 }}>
                    Dưới tồn tối thiểu: {formatNumber(filteredInventory.reduce((s, it) => s + (it?.low_stock ? 1 : 0), 0))}
                  </div>
                </div>
                <div className="field" style={{ margin: 0 }}>
                  <label htmlFor="reports-search">Tìm</label>
                  <input
                    id="reports-search"
                    placeholder="Tên hoặc SKU"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    style={{ width: 220 }}
                  />
                </div>
              </div>
              <div className="table-wrap" style={{ marginTop: 10 }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Tên</th>
                      <th>SKU</th>
                      <th style={{ textAlign: 'right' }}>Tồn</th>
                      <th style={{ textAlign: 'right' }}>Tối thiểu</th>
                      <th style={{ textAlign: 'right' }}>Nhập</th>
                      <th style={{ textAlign: 'right' }}>Xuất</th>
                      <th>Cảnh báo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredInventory.map((it) => (
                      <tr key={it.id} style={it.low_stock ? { background: 'rgba(255, 120, 80, 0.06)' } : undefined}>
                        <td>{it.name}</td>
                        <td>{it.sku}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.current_stock)}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.min_stock)}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.total_in)}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.total_out)}</td>
                        <td>{it.low_stock ? <span className="badge danger">Thấp</span> : ''}</td>
                      </tr>
                    ))}
                    {filteredInventory.length === 0 ? (
                      <tr>
                        <td colSpan={7} style={{ color: 'var(--muted)' }}>Không có dữ liệu</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {tab === 'low_stock' ? (
            <section className="card" style={{ padding: 12 }}>
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <h3 style={{ margin: 0 }}>Cảnh báo tồn kho</h3>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>Số mặt hàng: {formatNumber(lowStockItems.length)}</div>
              </div>
              <div className="table-wrap" style={{ marginTop: 10 }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Tên</th>
                      <th>SKU</th>
                      <th style={{ textAlign: 'right' }}>Tồn</th>
                      <th style={{ textAlign: 'right' }}>Tối thiểu</th>
                      <th style={{ textAlign: 'right' }}>Thiếu</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lowStockItems.map((it) => (
                      <tr key={it.id}>
                        <td>{it.name}</td>
                        <td>{it.sku}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.current_stock)}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.min_stock)}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.deficit)}</td>
                      </tr>
                    ))}
                    {lowStockItems.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ color: 'var(--muted)' }}>Không có cảnh báo</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
