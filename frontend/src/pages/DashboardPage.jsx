import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/api'
import { StatTile } from '../ui/StatTile'

function todayDateValue() {
  return new Date().toISOString().slice(0, 10)
}

function daysAgoDateValue(days) {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
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

export function DashboardPage() {
  const [from, setFrom] = useState(() => daysAgoDateValue(6))
  const [to, setTo] = useState(() => todayDateValue())
  const [denseTables, setDenseTables] = useState(false)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [revenueItems, setRevenueItems] = useState([])
  const [appointmentItems, setAppointmentItems] = useState([])
  const [inventoryItems, setInventoryItems] = useState([])
  const [lowStockItems, setLowStockItems] = useState([])

  const query = useMemo(() => {
    const params = new URLSearchParams()
    if (from) params.set('from', from)
    if (to) params.set('to', to)
    const s = params.toString()
    return s ? `?${s}` : ''
  }, [from, to])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [revenue, appointments, inventory, lowStock] = await Promise.all([
        apiFetch(`/api/reports/revenue${query}`),
        apiFetch(`/api/reports/appointments${query}`),
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
  }, [query])

  useEffect(() => {
    load()
  }, [load])

  const revenueTotal = useMemo(
    () => revenueItems.reduce((sum, it) => sum + Number(it?.revenue || 0), 0),
    [revenueItems],
  )
  const paymentsTotal = useMemo(
    () => revenueItems.reduce((sum, it) => sum + Number(it?.payments_count || 0), 0),
    [revenueItems],
  )

  const apptTotal = useMemo(
    () => appointmentItems.reduce((sum, it) => sum + Number(it?.total || 0), 0),
    [appointmentItems],
  )
  const apptArrived = useMemo(
    () => appointmentItems.reduce((sum, it) => sum + Number(it?.arrived || 0), 0),
    [appointmentItems],
  )
  const apptCancelled = useMemo(
    () => appointmentItems.reduce((sum, it) => sum + Number(it?.cancelled || 0), 0),
    [appointmentItems],
  )
  const apptNoShow = useMemo(
    () => appointmentItems.reduce((sum, it) => sum + Number(it?.no_show || 0), 0),
    [appointmentItems],
  )

  const lowStockCount = useMemo(() => lowStockItems.length, [lowStockItems])

  const topLowStock = useMemo(() => lowStockItems.slice(0, 8), [lowStockItems])
  const tableClassName = denseTables ? 'table dense' : 'table'

  return (
    <div className="panel">
      <div className="page-head">
        <div>
          <h2 style={{ margin: 0 }}>Tổng quan</h2>
          <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 6 }}>Tổng quan theo chi nhánh đang chọn</div>
        </div>
        <div className="row">
          <button className="btn btn-sm btn-ghost" type="button" onClick={() => setDenseTables((v) => !v)}>
            Mật độ bảng: {denseTables ? 'Gọn' : 'Thường'}
          </button>
          <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
            Tải lại
          </button>
        </div>
      </div>

      <div className="filters" style={{ marginTop: 12, alignItems: 'flex-end' }}>
        <div className="field" style={{ marginTop: 0 }}>
          <label>Từ ngày</label>
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </div>
        <div className="field" style={{ marginTop: 0 }}>
          <label>Đến ngày</label>
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </div>
        <div style={{ color: 'var(--muted)', fontSize: 12 }}>
          Mặc định 7 ngày gần nhất
        </div>
      </div>

      {loading ? <div style={{ marginTop: 12, color: 'var(--muted)' }}>Tải dữ liệu...</div> : null}
      {error ? <div className="error">{error}</div> : null}

      {!error ? (
        <div style={{ marginTop: 12, display: 'grid', gap: 12 }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 12,
            }}
          >
            <StatTile title="Doanh thu" value={`${formatMoney(revenueTotal)} VND`} sub={`${formatNumber(paymentsTotal)} giao dịch`} />
            <StatTile
              title="Lịch hẹn"
              value={formatNumber(apptTotal)}
              sub={`Đã đến: ${formatNumber(apptArrived)} | Hủy: ${formatNumber(apptCancelled)} | Không đến: ${formatNumber(apptNoShow)}`}
            />
            <StatTile title="Cảnh báo tồn kho" value={formatNumber(lowStockCount)} sub="Số mặt hàng dưới tồn tối thiểu" />
            <StatTile title="Dữ liệu" value={formatNumber(inventoryItems.length)} sub="Mặt hàng đang hoạt động" />
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: 12,
            }}
          >
            <section className="card" style={{ padding: 12 }}>
              <h3 style={{ margin: '0 0 10px 0' }}>Doanh thu theo ngày</h3>
              <div className="table-wrap" style={{ marginTop: 0 }}>
                <table className={tableClassName}>
                  <thead>
                    <tr>
                      <th>Ngày</th>
                      <th style={{ textAlign: 'right' }}>Doanh thu</th>
                      <th style={{ textAlign: 'right' }}>Giao dịch</th>
                    </tr>
                  </thead>
                  <tbody>
                    {revenueItems.map((it) => (
                      <tr key={`${it.day}-${it.staff_id || 'all'}-${it.service_id || 'all'}`}>
                        <td>{it.day}</td>
                        <td style={{ textAlign: 'right' }}>{formatMoney(it.revenue)}</td>
                        <td style={{ textAlign: 'right' }}>{formatNumber(it.payments_count)}</td>
                      </tr>
                    ))}
                    {revenueItems.length === 0 ? (
                      <tr>
                        <td colSpan={3} style={{ color: 'var(--muted)' }}>Không có dữ liệu</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="card" style={{ padding: 12 }}>
              <h3 style={{ margin: '0 0 10px 0' }}>Lịch hẹn theo ngày</h3>
              <div className="table-wrap" style={{ marginTop: 0 }}>
                <table className={tableClassName}>
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
          </div>

          <section className="card" style={{ padding: 12 }}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h3 style={{ margin: 0 }}>Cảnh báo tồn kho</h3>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Top {topLowStock.length} mặt hàng</div>
            </div>
            <div className="table-wrap" style={{ marginTop: 10 }}>
              <table className={tableClassName}>
                <thead>
                  <tr>
                    <th>Tên</th>
                    <th>SKU</th>
                    <th style={{ textAlign: 'right' }}>Tồn</th>
                    <th style={{ textAlign: 'right' }}>Tối thiểu</th>
                  </tr>
                </thead>
                <tbody>
                  {topLowStock.map((it) => (
                    <tr key={it.id}>
                      <td>{it.name}</td>
                      <td>{it.sku}</td>
                      <td style={{ textAlign: 'right' }}>{formatNumber(it.current_stock)}</td>
                      <td style={{ textAlign: 'right' }}>{formatNumber(it.min_stock)}</td>
                    </tr>
                  ))}
                  {topLowStock.length === 0 ? (
                    <tr>
                      <td colSpan={4} style={{ color: 'var(--muted)' }}>Không có cảnh báo</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  )
}
