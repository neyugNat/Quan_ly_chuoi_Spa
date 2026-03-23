import { Fragment, useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

function parseRequiredPositiveNumber(value) {
  const parsed = Number.parseFloat(String(value || '').trim())
  if (!Number.isFinite(parsed) || parsed <= 0) return null
  return parsed
}

function parseOptionalInt(value) {
  const text = String(value || '').trim()
  if (!text) return null
  const parsed = Number.parseInt(text, 10)
  return Number.isNaN(parsed) ? null : parsed
}

function resolveOnHand(item) {
  return item.current_stock ?? item.on_hand ?? item.on_hand_qty ?? item.qty_on_hand ?? item.quantity ?? 0
}

export function InventoryPage() {
  const [inventoryItems, setInventoryItems] = useState([])
  const [onHandItems, setOnHandItems] = useState([])
  const [transactions, setTransactions] = useState([])

  const [loading, setLoading] = useState(false)
  const [txLoading, setTxLoading] = useState(false)
  const [error, setError] = useState('')
  const [txError, setTxError] = useState('')

  const [name, setName] = useState('')
  const [unit, setUnit] = useState('')
  const [minStock, setMinStock] = useState('')
  const [status, setStatus] = useState('active')

  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editUnit, setEditUnit] = useState('')
  const [editMinStock, setEditMinStock] = useState('')
  const [editStatus, setEditStatus] = useState('active')
  const [updating, setUpdating] = useState(false)

  const [selectedItemId, setSelectedItemId] = useState('')
  const [transactionItemId, setTransactionItemId] = useState('')
  const [transactionType, setTransactionType] = useState('in')
  const [qty, setQty] = useState('')
  const [note, setNote] = useState('')

  const loadInventoryItems = useCallback(async () => {
    const data = await apiFetch('/api/inventory-items')
    setInventoryItems(data?.items || [])
  }, [])

  const loadOnHand = useCallback(async () => {
    const data = await apiFetch('/api/reports/inventory')
    setOnHandItems(data?.items || [])
  }, [])

  const loadTransactions = useCallback(async (itemId) => {
    if (!itemId) {
      setTransactions([])
      return
    }

    setTxLoading(true)
    setTxError('')
    try {
      const data = await apiFetch(`/api/stock-transactions?inventory_item_id=${encodeURIComponent(itemId)}`)
      setTransactions(data?.items || [])
    } catch (err) {
      setTxError(err?.data?.error || 'load_failed')
    } finally {
      setTxLoading(false)
    }
  }, [])

  const loadBase = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      await Promise.all([loadInventoryItems(), loadOnHand()])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [loadInventoryItems, loadOnHand])

  useEffect(() => {
    loadBase()
  }, [loadBase])

  useEffect(() => {
    loadTransactions(selectedItemId)
  }, [selectedItemId, loadTransactions])

  async function createInventoryItem(e) {
    e.preventDefault()
    setError('')

    const parsedMinStock = parseOptionalInt(minStock)
    if (String(minStock || '').trim() && parsedMinStock === null) {
      setError('invalid_min_stock')
      return
    }

    try {
      const payload = {
        name,
        min_stock: parsedMinStock,
      }
      if (unit.trim()) payload.unit = unit.trim()
      if (status) payload.status = status

      await apiFetch('/api/inventory-items', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setName('')
      setUnit('')
      setMinStock('')
      setStatus('active')
      await Promise.all([loadInventoryItems(), loadOnHand()])
    } catch (err) {
      setError(err?.data?.error || 'create_failed')
    }
  }

  function startEdit(item) {
    setEditingId(item.id)
    setEditName(item.name || '')
    setEditUnit(item.unit || '')
    setEditMinStock(String(item.min_stock ?? ''))
    setEditStatus(item.status || 'active')
  }

  function cancelEdit() {
    setEditingId(null)
    setEditName('')
    setEditUnit('')
    setEditMinStock('')
    setEditStatus('active')
  }

  async function updateInventoryItem(e) {
    e.preventDefault()
    if (!editingId) return
    setError('')

    const parsedMinStock = parseOptionalInt(editMinStock)
    if (String(editMinStock || '').trim() && parsedMinStock === null) {
      setError('invalid_min_stock')
      return
    }

    setUpdating(true)
    try {
      await apiFetch(`/api/inventory-items/${editingId}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editName,
          unit: editUnit,
          min_stock: parsedMinStock,
          status: editStatus,
        }),
      })
      cancelEdit()
      await Promise.all([loadInventoryItems(), loadOnHand()])
    } catch (err) {
      setError(err?.data?.error || 'update_failed')
    } finally {
      setUpdating(false)
    }
  }

  async function createStockTransaction(e) {
    e.preventDefault()
    setTxError('')

    if (!transactionItemId) {
      setTxError('inventory_item_id_required')
      return
    }

    const parsedQty = parseRequiredPositiveNumber(qty)
    if (parsedQty === null) {
      setTxError('qty_must_be_positive')
      return
    }

    try {
      const payload = {
        inventory_item_id: Number.parseInt(transactionItemId, 10),
        transaction_type: transactionType,
        qty: parsedQty,
      }
      if (note.trim()) payload.note = note.trim()

      await apiFetch('/api/stock-transactions', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setQty('')
      setNote('')
      setSelectedItemId(transactionItemId)
      await Promise.all([loadOnHand(), loadTransactions(transactionItemId)])
    } catch (err) {
      setTxError(err?.data?.error || 'create_failed')
    }
  }

  return (
    <div className="panel">
      <div className="page-head">
        <h2 style={{ margin: 0 }}>Kho</h2>
        <button className="btn btn-sm" type="button" onClick={loadBase} disabled={loading}>
          Tải lại
        </button>
      </div>

      <form onSubmit={createInventoryItem} style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Tạo vật tư</div>
        <div className="filters">
          <input placeholder="Tên vật tư" value={name} onChange={(e) => setName(e.target.value)} required />
          <input placeholder="Đơn vị" value={unit} onChange={(e) => setUnit(e.target.value)} />
          <input
            placeholder="Tồn tối thiểu"
            type="number"
            value={minStock}
            onChange={(e) => setMinStock(e.target.value)}
          />
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="active">Hoạt động</option>
            <option value="inactive">Ngừng hoạt động</option>
          </select>
          <button className="btn btn-sm" type="submit" disabled={loading}>
            Tạo
          </button>
        </div>
      </form>

      {error ? <div className="error">{error}</div> : null}

      <div className="table-wrap" style={{ marginTop: 14 }}>
        <h3 style={{ margin: '0 0 8px 0' }}>Danh mục vật tư</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên</th>
              <th>Đơn vị</th>
              <th>Tồn tối thiểu</th>
              <th>Trạng thái</th>
              <th>Tác vụ</th>
            </tr>
          </thead>
          <tbody>
            {inventoryItems.map((item) => (
              <Fragment key={item.id}>
                <tr onClick={() => startEdit(item)} style={{ cursor: 'pointer' }}>
                  <td>{item.id}</td>
                  <td>{item.name}</td>
                  <td>{item.unit || '-'}</td>
                  <td>{item.min_stock ?? '-'}</td>
                  <td>
                    {item.status === 'active' ? (
                      <span className="badge success">Hoạt động</span>
                    ) : item.status === 'inactive' ? (
                      <span className="badge warning">Ngừng</span>
                    ) : (
                      item.status
                    )}
                  </td>
                  <td>
                    <button
                      className="btn btn-sm"
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        startEdit(item)
                      }}
                    >
                      Sửa
                    </button>
                  </td>
                </tr>
                {editingId === item.id ? (
                  <tr>
                    <td colSpan={6}>
                      <form onSubmit={updateInventoryItem}>
                        <div className="row" style={{ flexWrap: 'wrap' }}>
                          <input
                            placeholder="Tên vật tư"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            required
                          />
                          <input placeholder="Đơn vị" value={editUnit} onChange={(e) => setEditUnit(e.target.value)} />
                          <input
                            placeholder="Mức tồn tối thiểu"
                            type="number"
                            value={editMinStock}
                            onChange={(e) => setEditMinStock(e.target.value)}
                          />
                          <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                            <option value="active">Hoạt động</option>
                            <option value="inactive">Ngừng hoạt động</option>
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
            {inventoryItems.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ color: 'var(--muted)' }}>Không có dữ liệu</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 18 }}>
        <h3 style={{ margin: '0 0 8px 0' }}>Nhập xuất kho</h3>
        <form onSubmit={createStockTransaction}>
          <div className="filters" style={{ marginBottom: 0 }}>
            <select value={transactionItemId} onChange={(e) => setTransactionItemId(e.target.value)} required>
              <option value="">Chọn vật tư</option>
              {inventoryItems.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <select value={transactionType} onChange={(e) => setTransactionType(e.target.value)}>
              <option value="in">Nhập</option>
              <option value="out">Xuất</option>
            </select>
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="Số lượng"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              required
            />
            <input placeholder="Ghi chú" value={note} onChange={(e) => setNote(e.target.value)} />
            <button className="btn btn-sm" type="submit" disabled={loading}>
              Ghi nhận
            </button>
          </div>
        </form>
        {txError ? <div className="error">{txError}</div> : null}
      </div>

      <div className="table-wrap" style={{ marginTop: 18 }}>
        <h3 style={{ margin: '0 0 8px 0' }}>Tồn kho</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên vật tư</th>
              <th>Tồn hiện tại</th>
            </tr>
          </thead>
          <tbody>
            {onHandItems.map((item, idx) => (
              <tr key={item.inventory_item_id || item.id || `${item.name || 'item'}-${idx}`}>
                <td>{item.inventory_item_id || item.id || '-'}</td>
                <td>{item.item_name || item.name || '-'}</td>
                <td>{resolveOnHand(item)}</td>
              </tr>
            ))}
            {onHandItems.length === 0 ? (
              <tr>
                <td colSpan={3} style={{ color: 'var(--muted)' }}>Không có dữ liệu</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="table-wrap" style={{ marginTop: 18 }}>
        <div className="filters" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
          <h3 style={{ margin: 0 }}>Lịch sử giao dịch</h3>
          <select value={selectedItemId} onChange={(e) => setSelectedItemId(e.target.value)} style={{ minWidth: 220 }}>
            <option value="">Chọn vật tư để xem</option>
            {inventoryItems.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>

        {txLoading ? <div style={{ marginTop: 8, color: 'var(--muted)' }}>Tải dữ liệu...</div> : null}

        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Loại</th>
              <th>Số lượng</th>
              <th>Thời gian</th>
              <th>Ghi chú</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx) => (
              <tr key={tx.id}>
                <td>{tx.id}</td>
                <td>{tx.transaction_type === 'in' ? 'Nhập' : tx.transaction_type === 'out' ? 'Xuất' : tx.transaction_type}</td>
                <td>{tx.qty}</td>
                <td>{tx.created_at || '-'}</td>
                <td>{tx.note || '-'}</td>
              </tr>
            ))}
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ color: 'var(--muted)' }}>Chọn vật tư để xem giao dịch</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
