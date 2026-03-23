import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/api'
import { Drawer } from '../ui/Drawer.jsx'

function todayDateValue() {
  return new Date().toISOString().slice(0, 10)
}

function displayDateTime(value) {
  if (!value) return ''
  return value.replace('T', ' ').slice(0, 16)
}

export function AppointmentsPage() {
  const [selectedDate, setSelectedDate] = useState(todayDateValue)
  const [appointments, setAppointments] = useState([])
  const [customers, setCustomers] = useState([])
  const [staffs, setStaffs] = useState([])
  const [resources, setResources] = useState([])
  const [customerPackages, setCustomerPackages] = useState([])

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedAppointment, setSelectedAppointment] = useState(null)

  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [conflicts, setConflicts] = useState([])

  const [customerId, setCustomerId] = useState('')
  const [customerPackageId, setCustomerPackageId] = useState('')
  const [sessionsUsed, setSessionsUsed] = useState('1')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [staffId, setStaffId] = useState('')
  const [resourceId, setResourceId] = useState('')
  const [serviceId, setServiceId] = useState('')
  const [note, setNote] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [appointmentsData, customersData, staffsData, resourcesData] = await Promise.all([
        apiFetch('/api/appointments'),
        apiFetch('/api/customers'),
        apiFetch('/api/staffs'),
        apiFetch('/api/resources'),
      ])
      setAppointments(appointmentsData.items || [])
      setCustomers(customersData.items || [])
      setStaffs(staffsData.items || [])
      setResources(resourcesData.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!customerId) {
      setCustomerPackages([])
      setCustomerPackageId('')
      setSessionsUsed('1')
      return
    }
    apiFetch(`/api/customer-packages?customer_id=${encodeURIComponent(customerId)}`)
      .then((data) => setCustomerPackages(data?.items || []))
      .catch(() => setCustomerPackages([]))
  }, [customerId])

  const dayItems = useMemo(
    () => appointments.filter((a) => String(a.start_time || '').slice(0, 10) === selectedDate),
    [appointments, selectedDate],
  )

  const customersById = useMemo(() => {
    const map = new Map()
    for (const c of customers) map.set(String(c.id), c)
    return map
  }, [customers])

  const staffsById = useMemo(() => {
    const map = new Map()
    for (const s of staffs) map.set(String(s.id), s)
    return map
  }, [staffs])

  const resourcesById = useMemo(() => {
    const map = new Map()
    for (const r of resources) map.set(String(r.id), r)
    return map
  }, [resources])

  function openDetails(appt) {
    setSelectedAppointment(appt)
    setDrawerOpen(true)
  }

  async function createAppointment(e) {
    e.preventDefault()
    setError('')
    setConflicts([])
    setSubmitting(true)
    try {
      const payload = {
        customer_id: Number.parseInt(customerId, 10),
        start_time: startTime,
        end_time: endTime,
      }
      if (customerPackageId) {
        payload.customer_package_id = Number.parseInt(customerPackageId, 10)
        payload.sessions_used = Number.parseInt(sessionsUsed || '1', 10)
      }
      if (staffId) payload.staff_id = Number.parseInt(staffId, 10)
      if (resourceId) payload.resource_id = Number.parseInt(resourceId, 10)
      if (serviceId) payload.service_id = Number.parseInt(serviceId, 10)
      if (note) payload.note = note

      await apiFetch('/api/appointments', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setStartTime('')
      setEndTime('')
      setStaffId('')
      setResourceId('')
      setServiceId('')
      setNote('')
      setCustomerPackageId('')
      setSessionsUsed('1')
      await load()
    } catch (err) {
      if (err?.status === 409 && err?.data?.error === 'conflict') {
        setError('conflict')
        setConflicts(err?.data?.conflicts || [])
      } else {
        setError(err?.data?.error || 'load_failed')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="panel">
      <div className="page-head">
        <h2 style={{ margin: 0 }}>Lịch hẹn</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      <div className="filters" style={{ marginTop: 12 }}>
        <div className="field" style={{ marginTop: 0 }}>
          <label htmlFor="appointments-date">Ngày</label>
          <input
            id="appointments-date"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
          />
        </div>
      </div>

      <form onSubmit={createAppointment} style={{ marginTop: 12 }}>
        <div className="row" style={{ flexWrap: 'wrap' }}>
          <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
            <option value="">Chọn khách hàng *</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name} ({c.phone})
              </option>
            ))}
          </select>

          <select value={customerPackageId} onChange={(e) => setCustomerPackageId(e.target.value)}>
            <option value="">Không dùng gói</option>
            {customerPackages.map((cp) => (
              <option key={cp.id} value={cp.id}>
                #{cp.id} (còn {cp.sessions_remaining}/{cp.sessions_total})
              </option>
            ))}
          </select>

          {customerPackageId ? (
            <input
              type="number"
              min={1}
              placeholder="Số buổi"
              value={sessionsUsed}
              onChange={(e) => setSessionsUsed(e.target.value)}
              style={{ width: 120 }}
            />
          ) : null}

          <input
            type="datetime-local"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            required
          />

          <input
            type="datetime-local"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            required
          />
        </div>

        <div className="row" style={{ marginTop: 8, flexWrap: 'wrap' }}>
          <select value={staffId} onChange={(e) => setStaffId(e.target.value)}>
            <option value="">Nhân viên (tùy chọn)</option>
            {staffs.map((s) => (
              <option key={s.id} value={s.id}>
                {s.full_name || s.name || `#${s.id}`}
              </option>
            ))}
          </select>

          <select value={resourceId} onChange={(e) => setResourceId(e.target.value)}>
            <option value="">Phòng/giường (tùy chọn)</option>
            {resources.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name || r.code || `#${r.id}`}
              </option>
            ))}
          </select>

          <input
            placeholder="service_id (tùy chọn)"
            value={serviceId}
            onChange={(e) => setServiceId(e.target.value)}
          />

          <input placeholder="Ghi chú" value={note} onChange={(e) => setNote(e.target.value)} style={{ width: 260 }} />

          <button className="btn" type="submit" disabled={submitting}>
            Tạo lịch
          </button>
        </div>
      </form>

      {error ? <div className="error">{error}</div> : null}

      {conflicts.length > 0 ? (
        <div style={{ marginTop: 10, border: '1px solid #f59e0b', borderRadius: 8, padding: 10 }}>
          <div style={{ fontWeight: 600 }}>Xung đột lịch:</div>
          <ul style={{ margin: '8px 0 0 18px' }}>
            {conflicts.map((c, idx) => (
              <li key={`${idx}-${c.appointment_id || 'conflict'}`}>
                Appointment #{c.appointment_id || '-'} ({c.kind || 'unknown'})
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="table-wrap" style={{ marginTop: 14 }}>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Khách hàng</th>
              <th>Bắt đầu</th>
              <th>Kết thúc</th>
              <th>Nhân viên</th>
              <th>Tài nguyên</th>
            </tr>
          </thead>
          <tbody>
            {dayItems.map((a) => (
              <tr key={a.id} onClick={() => openDetails(a)} style={{ cursor: 'pointer' }}>
                <td>{a.id}</td>
                <td>
                  {(() => {
                    const c = customersById.get(String(a.customer_id))
                    if (!c) return a.customer_id
                    return `${c.full_name || c.name || c.id} ${c.phone ? `(${c.phone})` : ''}`.trim()
                  })()}
                </td>
                <td>{displayDateTime(a.start_time)}</td>
                <td>{displayDateTime(a.end_time)}</td>
                <td>
                  {(() => {
                    if (!a.staff_id) return '-'
                    const s = staffsById.get(String(a.staff_id))
                    return s?.full_name || s?.name || a.staff_id
                  })()}
                </td>
                <td>
                  {(() => {
                    if (!a.resource_id) return '-'
                    const r = resourcesById.get(String(a.resource_id))
                    return r?.name || r?.code || a.resource_id
                  })()}
                </td>
              </tr>
            ))}
            {dayItems.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ color: 'var(--muted)' }}>Không có lịch hẹn trong ngày</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <Drawer
        open={drawerOpen}
        title={selectedAppointment ? `Lịch hẹn #${selectedAppointment.id}` : 'Lịch hẹn'}
        onClose={() => setDrawerOpen(false)}
      >
        {selectedAppointment ? (
          <div style={{ display: 'grid', gap: 10 }}>
            <div>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Khách hàng</div>
              <div style={{ fontWeight: 600 }}>
                {(() => {
                  const c = customersById.get(String(selectedAppointment.customer_id))
                  if (!c) return selectedAppointment.customer_id
                  return `${c.full_name || c.name || c.id} ${c.phone ? `(${c.phone})` : ''}`.trim()
                })()}
              </div>
            </div>

            <div className="row" style={{ alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>Bắt đầu</div>
                <div>{displayDateTime(selectedAppointment.start_time)}</div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>Kết thúc</div>
                <div>{displayDateTime(selectedAppointment.end_time)}</div>
              </div>
            </div>

            <div className="row" style={{ alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>Nhân viên</div>
                <div>
                  {(() => {
                    if (!selectedAppointment.staff_id) return '-'
                    const s = staffsById.get(String(selectedAppointment.staff_id))
                    return s?.full_name || s?.name || selectedAppointment.staff_id
                  })()}
                </div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>Tài nguyên</div>
                <div>
                  {(() => {
                    if (!selectedAppointment.resource_id) return '-'
                    const r = resourcesById.get(String(selectedAppointment.resource_id))
                    return r?.name || r?.code || selectedAppointment.resource_id
                  })()}
                </div>
              </div>
            </div>

            <div className="row" style={{ alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>service_id</div>
                <div>{selectedAppointment.service_id || '-'}</div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>Gói</div>
                <div>
                  {selectedAppointment.customer_package_id ? `#${selectedAppointment.customer_package_id}` : '-'}
                </div>
              </div>
            </div>

            <div>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Ghi chú</div>
              <div style={{ whiteSpace: 'pre-wrap' }}>{selectedAppointment.note || '-'}</div>
            </div>
          </div>
        ) : (
          <div style={{ color: 'var(--muted)' }}>Không có dữ liệu</div>
        )}
      </Drawer>
    </div>
  )
}
