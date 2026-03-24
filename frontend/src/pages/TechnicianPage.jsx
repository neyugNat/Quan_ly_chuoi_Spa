import { useCallback, useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { apiFetch } from '../lib/api'

function displayDateTime(value) {
  if (!value) return ''
  return String(value).replace('T', ' ').slice(0, 16)
}

function renderStatusBadge(status) {
  if (status === 'completed') return <span className="badge success">{status}</span>
  if (status === 'cancelled' || status === 'no_show') return <span className="badge danger">{status}</span>
  if (status === 'booked' || status === 'confirmed' || status === 'arrived' || status === 'in_service') {
    return <span className="badge warning">{status}</span>
  }
  return status
}

export function TechnicianPage() {
  const { user } = useAuth()
  const roles = useMemo(() => (user?.roles || []).map(String), [user])
  const isTechnician = roles.includes('technician')

  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [selectedId, setSelectedId] = useState(null)
  const selected = useMemo(() => items.find((i) => i.id === selectedId) || null, [items, selectedId])

  const [noteLoading, setNoteLoading] = useState(false)
  const [noteError, setNoteError] = useState('')
  const [subjective, setSubjective] = useState('')
  const [objective, setObjective] = useState('')
  const [assessment, setAssessment] = useState('')
  const [plan, setPlan] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch('/api/appointments')
      setItems(data?.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadNote = useCallback(async (appointmentId) => {
    if (!appointmentId) return
    setNoteLoading(true)
    setNoteError('')
    try {
      const data = await apiFetch(`/api/appointments/${appointmentId}/treatment-note`)
      setSubjective(data?.subjective_note || '')
      setObjective(data?.objective_note || '')
      setAssessment(data?.assessment_note || '')
      setPlan(data?.plan_note || '')
    } catch (err) {
      if (err?.status === 404) {
        setSubjective('')
        setObjective('')
        setAssessment('')
        setPlan('')
      } else {
        setNoteError(err?.data?.error || 'load_failed')
      }
    } finally {
      setNoteLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (selectedId) loadNote(selectedId)
  }, [selectedId, loadNote])

  async function checkIn(appointmentId) {
    setError('')
    try {
      await apiFetch(`/api/appointments/${appointmentId}/check-in`, { method: 'POST' })
      await load()
    } catch (err) {
      setError(err?.data?.error || 'check_in_failed')
    }
  }

  async function checkOut(appointmentId) {
    setError('')
    try {
      await apiFetch(`/api/appointments/${appointmentId}/check-out`, { method: 'POST' })
      await load()
    } catch (err) {
      setError(err?.data?.error || 'check_out_failed')
    }
  }

  async function saveNote(e) {
    e.preventDefault()
    if (!selectedId) return
    setNoteError('')
    setNoteLoading(true)
    try {
      await apiFetch(`/api/appointments/${selectedId}/treatment-note`, {
        method: 'PUT',
        body: JSON.stringify({
          subjective_note: subjective,
          objective_note: objective,
          assessment_note: assessment,
          plan_note: plan,
        }),
      })
    } catch (err) {
      setNoteError(err?.data?.error || 'save_failed')
    } finally {
      setNoteLoading(false)
    }
  }

  if (!isTechnician) return <Navigate to="/unauthorized" replace />

  return (
    <div className="panel">
      <div className="page-head">
        <h2 style={{ margin: 0 }}>Kỹ thuật viên</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      {error ? <div className="error">{error}</div> : null}

      <div className="split-grid">
        <div style={{ minWidth: 0 }}>
          <div className="table-wrap" style={{ marginTop: 0 }}>
            <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Khách</th>
                <th>Bắt đầu</th>
                <th>Kết thúc</th>
                <th>Status</th>
                <th>Tác vụ</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr
                  key={a.id}
                  onClick={() => setSelectedId(a.id)}
                  style={{ cursor: 'pointer', background: a.id === selectedId ? 'rgba(59,130,246,0.12)' : undefined }}
                >
                  <td>{a.id}</td>
                  <td>{a.customer_id}</td>
                  <td>{displayDateTime(a.start_time)}</td>
                  <td>{displayDateTime(a.end_time)}</td>
                  <td>{renderStatusBadge(a.status)}</td>
                  <td>
                    {a.status === 'booked' || a.status === 'confirmed' || a.status === 'arrived' ? (
                      <button
                        className="btn btn-sm"
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          checkIn(a.id)
                        }}
                      >
                        Bắt đầu
                      </button>
                    ) : null}
                    {a.status === 'in_service' ? (
                      <button
                        className="btn btn-sm"
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          checkOut(a.id)
                        }}
                      >
                        Hoàn tất
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
              {items.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ color: 'var(--muted)' }}>
                    Không có lịch
                  </td>
                </tr>
              ) : null}
            </tbody>
            </table>
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 600 }}>Ghi chú liệu trình</div>
          {!selected ? <div style={{ color: 'var(--muted)', marginTop: 8 }}>Chọn 1 lịch hẹn</div> : null}
          {noteError ? <div className="error">{noteError}</div> : null}

          {selected ? (
            <form onSubmit={saveNote} style={{ marginTop: 10 }}>
              <div className="field">
                <label>Chủ quan</label>
                <textarea value={subjective} onChange={(e) => setSubjective(e.target.value)} rows={2} />
              </div>
              <div className="field">
                <label>Khách quan</label>
                <textarea value={objective} onChange={(e) => setObjective(e.target.value)} rows={2} />
              </div>
              <div className="field">
                <label>Đánh giá</label>
                <textarea value={assessment} onChange={(e) => setAssessment(e.target.value)} rows={2} />
              </div>
              <div className="field">
                <label>Kế hoạch</label>
                <textarea value={plan} onChange={(e) => setPlan(e.target.value)} rows={2} />
              </div>
              <button className="btn" type="submit" disabled={noteLoading}>
                {noteLoading ? 'Đang lưu...' : 'Lưu ghi chú'}
              </button>
            </form>
          ) : null}
        </div>
      </div>
    </div>
  )
}
