import { Fragment, useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

function parseOptionalInt(value) {
  const text = String(value ?? '').trim()
  if (!text) return null
  const n = Number.parseInt(text, 10)
  return Number.isNaN(n) ? null : n
}

function parsePositiveNumber(value) {
  const n = Number.parseFloat(String(value ?? '').trim())
  if (!Number.isFinite(n) || n <= 0) return null
  return n
}

export function HrPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [staffs, setStaffs] = useState([])
  const [shifts, setShifts] = useState([])
  const [commissions, setCommissions] = useState([])

  const [staffFullName, setStaffFullName] = useState('')
  const [staffPhone, setStaffPhone] = useState('')
  const [staffTitle, setStaffTitle] = useState('')
  const [staffRole, setStaffRole] = useState('')
  const [staffSkillLevel, setStaffSkillLevel] = useState('')
  const [staffStatus, setStaffStatus] = useState('active')

  const [editingStaffId, setEditingStaffId] = useState(null)
  const [editStaffFullName, setEditStaffFullName] = useState('')
  const [editStaffPhone, setEditStaffPhone] = useState('')
  const [editStaffTitle, setEditStaffTitle] = useState('')
  const [editStaffRole, setEditStaffRole] = useState('')
  const [editStaffSkillLevel, setEditStaffSkillLevel] = useState('')
  const [editStaffStatus, setEditStaffStatus] = useState('active')
  const [savingStaff, setSavingStaff] = useState(false)

  const [shiftStaffId, setShiftStaffId] = useState('')
  const [shiftStart, setShiftStart] = useState('')
  const [shiftEnd, setShiftEnd] = useState('')
  const [shiftNote, setShiftNote] = useState('')
  const [shiftStatus, setShiftStatus] = useState('active')

  const [editingShiftId, setEditingShiftId] = useState(null)
  const [editShiftStaffId, setEditShiftStaffId] = useState('')
  const [editShiftStart, setEditShiftStart] = useState('')
  const [editShiftEnd, setEditShiftEnd] = useState('')
  const [editShiftNote, setEditShiftNote] = useState('')
  const [editShiftStatus, setEditShiftStatus] = useState('active')
  const [savingShift, setSavingShift] = useState(false)

  const [crStaffId, setCrStaffId] = useState('')
  const [crSourceType, setCrSourceType] = useState('service')
  const [crBaseAmount, setCrBaseAmount] = useState('')
  const [crRatePercent, setCrRatePercent] = useState('')
  const [crInvoiceId, setCrInvoiceId] = useState('')
  const [crStatus, setCrStatus] = useState('pending')

  const [editingCrId, setEditingCrId] = useState(null)
  const [editCrStaffId, setEditCrStaffId] = useState('')
  const [editCrSourceType, setEditCrSourceType] = useState('service')
  const [editCrBaseAmount, setEditCrBaseAmount] = useState('')
  const [editCrRatePercent, setEditCrRatePercent] = useState('')
  const [editCrInvoiceId, setEditCrInvoiceId] = useState('')
  const [editCrStatus, setEditCrStatus] = useState('pending')
  const [savingCr, setSavingCr] = useState(false)

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [staffData, shiftData, crData] = await Promise.all([
        apiFetch('/api/staffs'),
        apiFetch('/api/shifts'),
        apiFetch('/api/commission-records'),
      ])
      setStaffs(staffData?.items || [])
      setShifts(shiftData?.items || [])
      setCommissions(crData?.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  async function createStaff(e) {
    e.preventDefault()
    setError('')
    try {
      await apiFetch('/api/staffs', {
        method: 'POST',
        body: JSON.stringify({
          full_name: staffFullName,
          phone: staffPhone || null,
          title: staffTitle || null,
          role: staffRole || null,
          skill_level: staffSkillLevel || null,
          status: staffStatus,
        }),
      })
      setStaffFullName('')
      setStaffPhone('')
      setStaffTitle('')
      setStaffRole('')
      setStaffSkillLevel('')
      setStaffStatus('active')
      await loadAll()
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    }
  }

  function startEditStaff(s) {
    setEditingStaffId(s.id)
    setEditStaffFullName(s.full_name || '')
    setEditStaffPhone(s.phone || '')
    setEditStaffTitle(s.title || '')
    setEditStaffRole(s.role || '')
    setEditStaffSkillLevel(s.skill_level || '')
    setEditStaffStatus(s.status || 'active')
  }

  function cancelEditStaff() {
    setEditingStaffId(null)
    setEditStaffFullName('')
    setEditStaffPhone('')
    setEditStaffTitle('')
    setEditStaffRole('')
    setEditStaffSkillLevel('')
    setEditStaffStatus('active')
  }

  async function updateStaff(e) {
    e.preventDefault()
    if (!editingStaffId) return
    setError('')
    setSavingStaff(true)
    try {
      await apiFetch(`/api/staffs/${editingStaffId}`, {
        method: 'PUT',
        body: JSON.stringify({
          full_name: editStaffFullName,
          phone: editStaffPhone || null,
          title: editStaffTitle || null,
          role: editStaffRole || null,
          skill_level: editStaffSkillLevel || null,
          status: editStaffStatus,
        }),
      })
      cancelEditStaff()
      await loadAll()
    } catch (err) {
      setError(err?.data?.error || 'update_failed')
    } finally {
      setSavingStaff(false)
    }
  }

  async function createShift(e) {
    e.preventDefault()
    setError('')

    const parsedStaffId = parseOptionalInt(shiftStaffId)
    if (!parsedStaffId) {
      setError('staff_id_required')
      return
    }
    if (!shiftStart || !shiftEnd) {
      setError('missing_fields')
      return
    }

    try {
      await apiFetch('/api/shifts', {
        method: 'POST',
        body: JSON.stringify({
          staff_id: parsedStaffId,
          start_time: shiftStart,
          end_time: shiftEnd,
          note: shiftNote || null,
          status: shiftStatus,
        }),
      })
      setShiftStaffId('')
      setShiftStart('')
      setShiftEnd('')
      setShiftNote('')
      setShiftStatus('active')
      await loadAll()
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    }
  }

  function startEditShift(s) {
    setEditingShiftId(s.id)
    setEditShiftStaffId(String(s.staff_id ?? ''))
    setEditShiftStart(String(s.start_time || '').slice(0, 16))
    setEditShiftEnd(String(s.end_time || '').slice(0, 16))
    setEditShiftNote(s.note || '')
    setEditShiftStatus(s.status || 'active')
  }

  function cancelEditShift() {
    setEditingShiftId(null)
    setEditShiftStaffId('')
    setEditShiftStart('')
    setEditShiftEnd('')
    setEditShiftNote('')
    setEditShiftStatus('active')
  }

  async function updateShift(e) {
    e.preventDefault()
    if (!editingShiftId) return
    setError('')
    setSavingShift(true)

    const parsedStaffId = parseOptionalInt(editShiftStaffId)
    if (!parsedStaffId) {
      setError('staff_id_required')
      setSavingShift(false)
      return
    }
    if (!editShiftStart || !editShiftEnd) {
      setError('missing_fields')
      setSavingShift(false)
      return
    }

    try {
      await apiFetch(`/api/shifts/${editingShiftId}`, {
        method: 'PUT',
        body: JSON.stringify({
          staff_id: parsedStaffId,
          start_time: editShiftStart,
          end_time: editShiftEnd,
          note: editShiftNote || null,
          status: editShiftStatus,
        }),
      })
      cancelEditShift()
      await loadAll()
    } catch (err) {
      setError(err?.data?.error || 'update_failed')
    } finally {
      setSavingShift(false)
    }
  }

  async function createCommissionRecord(e) {
    e.preventDefault()
    setError('')

    const parsedStaffId = parseOptionalInt(crStaffId)
    const parsedInvoiceId = parseOptionalInt(crInvoiceId)
    const baseAmount = parsePositiveNumber(crBaseAmount)
    const ratePercent = parsePositiveNumber(crRatePercent)
    if (!parsedStaffId || baseAmount === null || ratePercent === null) {
      setError('missing_fields')
      return
    }

    try {
      const payload = {
        staff_id: parsedStaffId,
        source_type: crSourceType,
        base_amount: baseAmount,
        rate_percent: ratePercent,
        status: crStatus,
      }
      if (parsedInvoiceId) payload.invoice_id = parsedInvoiceId
      await apiFetch('/api/commission-records', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setCrStaffId('')
      setCrSourceType('service')
      setCrBaseAmount('')
      setCrRatePercent('')
      setCrInvoiceId('')
      setCrStatus('pending')
      await loadAll()
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    }
  }

  function startEditCr(c) {
    setEditingCrId(c.id)
    setEditCrStaffId(String(c.staff_id ?? ''))
    setEditCrSourceType(c.source_type || 'service')
    setEditCrBaseAmount(String(c.base_amount ?? ''))
    setEditCrRatePercent(String(c.rate_percent ?? ''))
    setEditCrInvoiceId(String(c.invoice_id ?? ''))
    setEditCrStatus(c.status || 'pending')
  }

  function cancelEditCr() {
    setEditingCrId(null)
    setEditCrStaffId('')
    setEditCrSourceType('service')
    setEditCrBaseAmount('')
    setEditCrRatePercent('')
    setEditCrInvoiceId('')
    setEditCrStatus('pending')
  }

  async function updateCommissionRecord(e) {
    e.preventDefault()
    if (!editingCrId) return
    setError('')
    setSavingCr(true)

    const parsedStaffId = parseOptionalInt(editCrStaffId)
    const parsedInvoiceId = parseOptionalInt(editCrInvoiceId)
    const baseAmount = parsePositiveNumber(editCrBaseAmount)
    const ratePercent = parsePositiveNumber(editCrRatePercent)
    if (!parsedStaffId || baseAmount === null || ratePercent === null) {
      setError('missing_fields')
      setSavingCr(false)
      return
    }

    try {
      const payload = {
        staff_id: parsedStaffId,
        source_type: editCrSourceType,
        base_amount: baseAmount,
        rate_percent: ratePercent,
        status: editCrStatus,
      }
      if (parsedInvoiceId) payload.invoice_id = parsedInvoiceId
      await apiFetch(`/api/commission-records/${editingCrId}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      })
      cancelEditCr()
      await loadAll()
    } catch (err) {
      setError(err?.data?.error || 'update_failed')
    } finally {
      setSavingCr(false)
    }
  }

  return (
    <div className="panel">
      <div className="page-head">
        <h2 style={{ margin: 0 }}>Nhân sự / Ca làm / Hoa hồng</h2>
        <button className="btn btn-sm" type="button" onClick={loadAll} disabled={loading}>
          Tải lại
        </button>
      </div>

      {error ? <div className="error">{error}</div> : null}

      <div style={{ marginTop: 14 }}>
        <h3 style={{ margin: '0 0 8px 0' }}>Nhân sự</h3>
        <form onSubmit={createStaff}>
          <div className="filters" style={{ marginBottom: 0 }}>
            <input placeholder="Họ tên" value={staffFullName} onChange={(e) => setStaffFullName(e.target.value)} required />
            <input placeholder="Điện thoại" value={staffPhone} onChange={(e) => setStaffPhone(e.target.value)} />
            <input placeholder="Chức danh" value={staffTitle} onChange={(e) => setStaffTitle(e.target.value)} />
            <input placeholder="Vai trò" value={staffRole} onChange={(e) => setStaffRole(e.target.value)} />
            <input placeholder="Cấp độ kỹ năng" value={staffSkillLevel} onChange={(e) => setStaffSkillLevel(e.target.value)} />
            <select value={staffStatus} onChange={(e) => setStaffStatus(e.target.value)}>
              <option value="active">Hoạt động</option>
              <option value="inactive">Ngừng hoạt động</option>
            </select>
            <button className="btn btn-sm" type="submit" disabled={loading}>
              Tạo
            </button>
          </div>
        </form>

        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Họ tên</th>
                <th>Điện thoại</th>
                <th>Chức danh</th>
                <th>Trạng thái</th>
                <th>Tác vụ</th>
              </tr>
            </thead>
            <tbody>
              {staffs.map((s) => (
                <Fragment key={s.id}>
                  <tr onClick={() => startEditStaff(s)} style={{ cursor: 'pointer' }}>
                    <td>{s.id}</td>
                    <td>{s.full_name}</td>
                    <td>{s.phone || '-'}</td>
                    <td>{s.title || '-'}</td>
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
                          startEditStaff(s)
                        }}
                      >
                        Sửa
                      </button>
                    </td>
                  </tr>
                  {editingStaffId === s.id ? (
                    <tr>
                      <td colSpan={6}>
                        <form onSubmit={updateStaff}>
                          <div className="row" style={{ flexWrap: 'wrap' }}>
                            <input value={editStaffFullName} onChange={(e) => setEditStaffFullName(e.target.value)} required />
                            <input value={editStaffPhone} onChange={(e) => setEditStaffPhone(e.target.value)} placeholder="Điện thoại" />
                            <input value={editStaffTitle} onChange={(e) => setEditStaffTitle(e.target.value)} placeholder="Chức danh" />
                            <input value={editStaffRole} onChange={(e) => setEditStaffRole(e.target.value)} placeholder="Vai trò" />
                            <input
                              value={editStaffSkillLevel}
                              onChange={(e) => setEditStaffSkillLevel(e.target.value)}
                              placeholder="Cấp độ kỹ năng"
                            />
                            <select value={editStaffStatus} onChange={(e) => setEditStaffStatus(e.target.value)}>
                              <option value="active">active</option>
                              <option value="inactive">inactive</option>
                            </select>
                            <button className="btn" type="submit" disabled={savingStaff}>
                  {savingStaff ? 'Đang lưu...' : 'Lưu'}
                </button>
                <button className="btn" type="button" onClick={cancelEditStaff} disabled={savingStaff}>
                  Hủy
                </button>
                          </div>
                        </form>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
              {staffs.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: 10, color: 'var(--muted)' }}>
              Không có dữ liệu
            </td>
          </tr>
        ) : null}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <h3 style={{ margin: '0 0 8px 0' }}>Ca làm</h3>
        <form onSubmit={createShift}>
          <div className="row" style={{ flexWrap: 'wrap' }}>
            <select value={shiftStaffId} onChange={(e) => setShiftStaffId(e.target.value)} required>
              <option value="">Chọn nhân sự</option>
              {staffs.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name}
                </option>
              ))}
            </select>
            <input type="datetime-local" value={shiftStart} onChange={(e) => setShiftStart(e.target.value)} required />
            <input type="datetime-local" value={shiftEnd} onChange={(e) => setShiftEnd(e.target.value)} required />
            <input placeholder="Ghi chú" value={shiftNote} onChange={(e) => setShiftNote(e.target.value)} />
            <select value={shiftStatus} onChange={(e) => setShiftStatus(e.target.value)}>
              <option value="active">active</option>
              <option value="inactive">inactive</option>
            </select>
            <button className="btn" type="submit" disabled={loading}>
            Tạo
            </button>
          </div>
        </form>

        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nhân sự</th>
                <th>Bắt đầu</th>
                <th>Kết thúc</th>
                <th>Trạng thái</th>
                <th>Tác vụ</th>
              </tr>
            </thead>
            <tbody>
              {shifts.map((s) => (
                <Fragment key={s.id}>
                  <tr onClick={() => startEditShift(s)} style={{ cursor: 'pointer' }}>
                    <td>{s.id}</td>
                    <td>{s.staff_id}</td>
                    <td>{String(s.start_time || '').slice(0, 16)}</td>
                    <td>{String(s.end_time || '').slice(0, 16)}</td>
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
                        className="btn"
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          startEditShift(s)
                        }}
                      >
                    Sửa
                      </button>
                    </td>
                  </tr>
                  {editingShiftId === s.id ? (
                    <tr>
                      <td colSpan={6}>
                        <form onSubmit={updateShift}>
                          <div className="row" style={{ flexWrap: 'wrap' }}>
                            <select value={editShiftStaffId} onChange={(e) => setEditShiftStaffId(e.target.value)} required>
                              <option value="">Chọn nhân sự</option>
                              {staffs.map((st) => (
                                <option key={st.id} value={st.id}>
                                  {st.full_name}
                                </option>
                              ))}
                            </select>
                            <input
                              type="datetime-local"
                              value={editShiftStart}
                              onChange={(e) => setEditShiftStart(e.target.value)}
                              required
                            />
                            <input
                              type="datetime-local"
                              value={editShiftEnd}
                              onChange={(e) => setEditShiftEnd(e.target.value)}
                              required
                            />
                            <input value={editShiftNote} onChange={(e) => setEditShiftNote(e.target.value)} placeholder="Ghi chú" />
                            <select value={editShiftStatus} onChange={(e) => setEditShiftStatus(e.target.value)}>
                              <option value="active">active</option>
                              <option value="inactive">inactive</option>
                            </select>
                            <button className="btn" type="submit" disabled={savingShift}>
                  {savingShift ? 'Đang lưu...' : 'Lưu'}
                </button>
                <button className="btn" type="button" onClick={cancelEditShift} disabled={savingShift}>
                  Hủy
                </button>
                          </div>
                        </form>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
              {shifts.length === 0 ? (
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

      <div style={{ marginTop: 18 }}>
        <h3 style={{ margin: '0 0 8px 0' }}>Hoa hồng</h3>
        <form onSubmit={createCommissionRecord}>
          <div className="row" style={{ flexWrap: 'wrap' }}>
            <select value={crStaffId} onChange={(e) => setCrStaffId(e.target.value)} required>
              <option value="">Chọn nhân sự</option>
              {staffs.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name}
                </option>
              ))}
            </select>
            <select value={crSourceType} onChange={(e) => setCrSourceType(e.target.value)}>
              <option value="service">service</option>
              <option value="product">product</option>
              <option value="package">package</option>
            </select>
            <input
              placeholder="Số tiền cơ sở"
              type="number"
              step="0.01"
              value={crBaseAmount}
              onChange={(e) => setCrBaseAmount(e.target.value)}
              required
            />
            <input
              placeholder="Tỷ lệ %"
              type="number"
              step="0.01"
              value={crRatePercent}
              onChange={(e) => setCrRatePercent(e.target.value)}
              required
            />
            <input placeholder="invoice_id (tùy chọn)" value={crInvoiceId} onChange={(e) => setCrInvoiceId(e.target.value)} />
            <select value={crStatus} onChange={(e) => setCrStatus(e.target.value)}>
              <option value="pending">pending</option>
              <option value="paid">paid</option>
              <option value="cancelled">cancelled</option>
            </select>
            <button className="btn" type="submit" disabled={loading}>
            Tạo
            </button>
          </div>
        </form>

        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nhân sự</th>
                <th>Loại</th>
                <th>Cơ sở</th>
                <th>Tỷ lệ</th>
                <th>Hoa hồng</th>
                <th>Trạng thái</th>
                <th>Tác vụ</th>
              </tr>
            </thead>
            <tbody>
              {commissions.map((c) => (
                <Fragment key={c.id}>
                  <tr onClick={() => startEditCr(c)} style={{ cursor: 'pointer' }}>
                    <td>{c.id}</td>
                    <td>{c.staff_id}</td>
                    <td>{c.source_type}</td>
                    <td>{c.base_amount}</td>
                    <td>{c.rate_percent}</td>
                    <td>{c.commission_amount}</td>
                    <td>
                      {c.status === 'paid' ? (
                        <span className="badge success">Đã trả</span>
                      ) : c.status === 'pending' ? (
                        <span className="badge warning">Chờ trả</span>
                      ) : c.status === 'cancelled' ? (
                        <span className="badge danger">Đã hủy</span>
                      ) : (
                        c.status
                      )}
                    </td>
                    <td>
                      <button
                        className="btn"
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          startEditCr(c)
                        }}
                      >
                    Sửa
                      </button>
                    </td>
                  </tr>
                  {editingCrId === c.id ? (
                    <tr>
                      <td colSpan={8}>
                        <form onSubmit={updateCommissionRecord}>
                          <div className="row" style={{ flexWrap: 'wrap' }}>
                            <select value={editCrStaffId} onChange={(e) => setEditCrStaffId(e.target.value)} required>
                              <option value="">Chọn nhân sự</option>
                              {staffs.map((s) => (
                                <option key={s.id} value={s.id}>
                                  {s.full_name}
                                </option>
                              ))}
                            </select>
                            <select value={editCrSourceType} onChange={(e) => setEditCrSourceType(e.target.value)}>
                              <option value="service">service</option>
                              <option value="product">product</option>
                              <option value="package">package</option>
                            </select>
                            <input
                              type="number"
                              step="0.01"
                              value={editCrBaseAmount}
                              onChange={(e) => setEditCrBaseAmount(e.target.value)}
                              placeholder="Cơ sở"
                              required
                            />
                            <input
                              type="number"
                              step="0.01"
                              value={editCrRatePercent}
                              onChange={(e) => setEditCrRatePercent(e.target.value)}
                              placeholder="Tỷ lệ %"
                              required
                            />
                            <input
                              value={editCrInvoiceId}
                              onChange={(e) => setEditCrInvoiceId(e.target.value)}
                              placeholder="invoice_id"
                            />
                            <select value={editCrStatus} onChange={(e) => setEditCrStatus(e.target.value)}>
                              <option value="pending">pending</option>
                              <option value="paid">paid</option>
                              <option value="cancelled">cancelled</option>
                            </select>
                            <button className="btn" type="submit" disabled={savingCr}>
                  {savingCr ? 'Đang lưu...' : 'Lưu'}
                </button>
                <button className="btn" type="button" onClick={cancelEditCr} disabled={savingCr}>
                  Hủy
                </button>
                          </div>
                        </form>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
              {commissions.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ color: 'var(--muted)' }}>
              Không có dữ liệu
            </td>
          </tr>
        ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
