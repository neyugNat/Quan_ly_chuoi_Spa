import { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

export function AuditLogsPage() {
  const [items, setItems] = useState([])
  const [limit, setLimit] = useState('50')
  const [action, setAction] = useState('')
  const [userId, setUserId] = useState('')
  const [branchId, setBranchId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (limit.trim()) params.set('limit', limit.trim())
      if (action.trim()) params.set('action', action.trim())
      if (userId.trim()) params.set('user_id', userId.trim())
      if (branchId.trim()) params.set('branch_id', branchId.trim())

      const query = params.toString()
      const data = await apiFetch(`/api/audit-logs${query ? `?${query}` : ''}`)
      setItems(data?.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [limit, action, userId, branchId])

  useEffect(() => {
    load()
  }, [load])

  function handleFilterSubmit(e) {
    e.preventDefault()
    load()
  }

  return (
    <div className="panel">
      <div className="page-head">
        <h2 style={{ margin: 0 }}>Nhật ký hệ thống</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      <form onSubmit={handleFilterSubmit}>
        <div className="filters">
          <input
            placeholder="limit"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            style={{ width: 110 }}
          />
          <input
            placeholder="action"
            value={action}
            onChange={(e) => setAction(e.target.value)}
            style={{ width: 180 }}
          />
          <input
            placeholder="user_id"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            style={{ width: 140 }}
          />
          <input
            placeholder="branch_id"
            value={branchId}
            onChange={(e) => setBranchId(e.target.value)}
            style={{ width: 140 }}
          />
          <button className="btn" type="submit" disabled={loading}>
            Lọc
          </button>
        </div>
      </form>
      
      {error ? <div className="error">{error}</div> : null}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Thời gian</th>
              <th>Action</th>
              <th>User ID</th>
              <th>Branch ID</th>
              <th>Entity</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.created_at || '-'}</td>
                <td>{item.action || '-'}</td>
                <td>{item.user_id || '-'}</td>
                <td>{item.branch_id || '-'}</td>
                <td>{item.entity || '-'}</td>
              </tr>
            ))}
            {items.length === 0 ? (
              <tr>
                <td colSpan={6}>
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
