import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../auth/AuthContext.jsx'
import { apiFetch } from '../lib/api'

function safeParseJson(value) {
  if (value === null || value === undefined) return null
  if (typeof value === 'object') return value
  const text = String(value).trim()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function formatMoney(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value ?? '')
  return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 }).format(n)
}

function normalizeLineItems(lineItemsJson) {
  const parsed = safeParseJson(lineItemsJson)
  if (Array.isArray(parsed)) return parsed
  if (parsed && typeof parsed === 'object' && Array.isArray(parsed.items)) return parsed.items
  return []
}

export function PosPage() {
  const { user } = useAuth()
  const roles = useMemo(() => (user?.roles || []).map(String), [user])
  const isManager = roles.includes('super_admin') || roles.includes('branch_manager')

  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [selectedInvoiceId, setSelectedInvoiceId] = useState(null)
  const selectedInvoice = useMemo(
    () => invoices.find((i) => String(i.id) === String(selectedInvoiceId)) || null,
    [invoices, selectedInvoiceId],
  )

  const [payments, setPayments] = useState([])
  const [paymentsLoading, setPaymentsLoading] = useState(false)

  const [customerId, setCustomerId] = useState('')
  const [creatingInvoice, setCreatingInvoice] = useState(false)

  const [newItems, setNewItems] = useState([{ name: '', qty: '1', unit_price: '' }])

  const [payAmount, setPayAmount] = useState('')
  const [payMethod, setPayMethod] = useState('cash')
  const [payReferenceCode, setPayReferenceCode] = useState('')
  const [creatingPayment, setCreatingPayment] = useState(false)

  const [refundAmount, setRefundAmount] = useState('')
  const [refundMethod, setRefundMethod] = useState('cash')
  const [refundReferenceCode, setRefundReferenceCode] = useState('')
  const [creatingRefund, setCreatingRefund] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch('/api/invoices')
      setInvoices(data.items || [])
    } catch (err) {
      setError(err?.data?.error || 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadPayments = useCallback(async (invoiceId) => {
    if (!invoiceId) return
    setPaymentsLoading(true)
    setError('')
    try {
      const data = await apiFetch(`/api/invoices/${invoiceId}/payments`)
      setPayments(data.items || data.payments || [])
    } catch (err) {
      setPayments([])
      setError(err?.data?.error || 'load_payments_failed')
    } finally {
      setPaymentsLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!selectedInvoiceId) {
      setPayments([])
      return
    }
    loadPayments(selectedInvoiceId)
  }, [selectedInvoiceId, loadPayments])

  function updateItem(idx, patch) {
    setNewItems((prev) => prev.map((it, i) => (i === idx ? { ...it, ...patch } : it)))
  }

  function addItem() {
    setNewItems((prev) => [...prev, { name: '', qty: '1', unit_price: '' }])
  }

  function removeItem(idx) {
    setNewItems((prev) => prev.filter((_, i) => i !== idx))
  }

  async function createRetailInvoice(e) {
    e.preventDefault()
    setError('')
    setCreatingInvoice(true)
    try {
      const lineItems = newItems
        .map((it) => ({
          name: String(it.name || '').trim(),
          qty: Number.parseFloat(it.qty),
          unit_price: Number.parseFloat(it.unit_price),
        }))
        .filter((it) => it.name && Number.isFinite(it.qty) && Number.isFinite(it.unit_price))

      const totalAmount = lineItems.reduce((sum, it) => sum + it.qty * it.unit_price, 0)
      if (!Number.isFinite(totalAmount) || totalAmount < 0) {
        setError('invalid_total_amount')
        return
      }

      const payload = {
        line_items_json: lineItems,
        total_amount: totalAmount,
      }

      const parsedCustomerId = String(customerId || '').trim()
      if (parsedCustomerId) payload.customer_id = Number.parseInt(parsedCustomerId, 10)

      const created = await apiFetch('/api/invoices', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setCustomerId('')
      setNewItems([{ name: '', qty: '1', unit_price: '' }])
      await load()

      const newId = created?.item?.id || created?.id
      if (newId) setSelectedInvoiceId(String(newId))
    } catch (err) {
      setError(err?.data?.error || 'create_invoice_failed')
    } finally {
      setCreatingInvoice(false)
    }
  }

  async function createPayment(e) {
    e.preventDefault()
    if (!selectedInvoice) return
    setError('')
    setCreatingPayment(true)
    try {
      const payload = {
        invoice_id: selectedInvoice.id,
        amount: Number.parseFloat(payAmount),
        method: payMethod,
      }
      if (payReferenceCode) payload.reference_code = payReferenceCode

      await apiFetch('/api/payments', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setPayAmount('')
      setPayReferenceCode('')
      await load()
      await loadPayments(selectedInvoice.id)
    } catch (err) {
      setError(err?.data?.error || 'create_payment_failed')
    } finally {
      setCreatingPayment(false)
    }
  }

  async function voidInvoice(invoiceId) {
    if (!invoiceId) return
    setError('')
    try {
      await apiFetch(`/api/invoices/${invoiceId}/void`, { method: 'POST' })
      await load()
      if (String(selectedInvoiceId) === String(invoiceId)) {
        await loadPayments(invoiceId)
      }
    } catch (err) {
      setError(err?.data?.error || 'void_failed')
    }
  }

  async function refundInvoice(e) {
    e.preventDefault()
    if (!selectedInvoice) return
    setError('')
    setCreatingRefund(true)
    try {
      const payload = {
        amount: Number.parseFloat(refundAmount),
        method: refundMethod,
      }
      if (refundReferenceCode) payload.reference_code = refundReferenceCode

      await apiFetch(`/api/invoices/${selectedInvoice.id}/refund`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setRefundAmount('')
      setRefundReferenceCode('')
      await load()
      await loadPayments(selectedInvoice.id)
    } catch (err) {
      setError(err?.data?.error || 'refund_failed')
    } finally {
      setCreatingRefund(false)
    }
  }

  const selectedLineItems = useMemo(
    () => (selectedInvoice ? normalizeLineItems(selectedInvoice.line_items_json) : []),
    [selectedInvoice],
  )

  return (
    <div className="panel">
      <div className="page-head">
        <h2 style={{ margin: 0 }}>POS / Hóa đơn</h2>
        <button className="btn btn-sm" type="button" onClick={load} disabled={loading}>
          Tải lại
        </button>
      </div>

      <form onSubmit={createRetailInvoice} style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Tạo hóa đơn bán lẻ</div>
        <div className="row" style={{ flexWrap: 'wrap' }}>
          <input
            placeholder="customer_id (tùy chọn)"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            style={{ width: 220 }}
          />
          <button className="btn" type="submit" disabled={creatingInvoice || loading}>
            {creatingInvoice ? 'Đang tạo...' : 'Tạo hóa đơn'}
          </button>
        </div>

        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table className="table">
            <thead>
              <tr>
                <th>Tên</th>
                <th>Qty</th>
                <th>Đơn giá</th>
                <th>Tác vụ</th>
              </tr>
            </thead>
            <tbody>
              {newItems.map((it, idx) => (
                <tr key={idx}>
                  <td>
                    <input
                      placeholder="Sản phẩm/Dịch vụ"
                      value={it.name}
                      onChange={(e) => updateItem(idx, { name: e.target.value })}
                      style={{ width: '100%' }}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      value={it.qty}
                      onChange={(e) => updateItem(idx, { qty: e.target.value })}
                      style={{ width: 110 }}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      value={it.unit_price}
                      onChange={(e) => updateItem(idx, { unit_price: e.target.value })}
                      style={{ width: 140 }}
                    />
                  </td>
                  <td>
                    <button
                      className="btn btn-sm btn-danger"
                      type="button"
                      onClick={() => removeItem(idx)}
                      disabled={newItems.length <= 1}
                    >
                      Xóa
                    </button>
                  </td>
                </tr>
              ))}
              <tr>
                <td colSpan={4}>
                  <button className="btn btn-sm" type="button" onClick={addItem}>
                    Thêm dòng
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </form>

      {error ? <div className="error" style={{ marginTop: 12 }}>{error}</div> : null}

      <div className="split-grid">
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Danh sách hóa đơn</div>
          <div className="table-wrap" style={{ marginTop: 0 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Loại</th>
                  <th>Status</th>
                  <th>Tổng</th>
                  <th>Ngày</th>
                  <th>Tác vụ</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <Fragment key={inv.id}>
                    <tr
                      onClick={() => setSelectedInvoiceId(String(inv.id))}
                      style={{ cursor: 'pointer', background: String(inv.id) === String(selectedInvoiceId) ? 'rgba(59, 130, 246, 0.08)' : undefined }}
                    >
                      <td>{inv.id}</td>
                      <td>{inv.kind || inv.type || '-'}</td>
                      <td>{inv.status || '-'}</td>
                      <td>{formatMoney(inv.total_amount ?? inv.total ?? inv.amount_total ?? '-')}</td>
                      <td>{String(inv.created_at || inv.createdAt || inv.created_time || '').replace('T', ' ').slice(0, 16) || '-'}</td>
                      <td>
                        <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                          <button
                            className="btn"
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setSelectedInvoiceId(String(inv.id))
                            }}
                          >
                            Xem
                          </button>
                          {isManager ? (
                            <button
                              className="btn"
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                voidInvoice(inv.id)
                              }}
                              disabled={String(inv.status) === 'voided' || Number(inv.paid_amount || 0) > 0}
                            >
                              Void
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  </Fragment>
                ))}
                {invoices.length === 0 ? (
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

        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Chi tiết</div>
          {!selectedInvoice ? (
            <div style={{ color: 'var(--muted)' }}>Chọn 1 hóa đơn để xem chi tiết</div>
          ) : (
            <div style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 10 }}>
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <div>
          <div style={{ fontWeight: 700 }}>Hóa đơn #{selectedInvoice.id}</div>
                  <div style={{ color: 'var(--muted)', fontSize: 13 }}>
                    {selectedInvoice.kind || selectedInvoice.type || 'invoice'} · {selectedInvoice.status || '-'}
                  </div>
                </div>
                <button className="btn" type="button" onClick={() => loadPayments(selectedInvoice.id)} disabled={paymentsLoading}>
          {paymentsLoading ? 'Đang tải...' : 'Tải thanh toán'}
                </button>
              </div>

              <div style={{ marginTop: 10 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Line items</div>
                {selectedLineItems.length === 0 ? (
                  <div style={{ color: 'var(--muted)' }}>Không có line items (hoặc parse thất bại)</div>
                ) : (
                  <div className="table-wrap" style={{ marginTop: 0 }}>
                    <table className="table dense">
                      <thead>
                        <tr>
                          <th>Tên</th>
                          <th>Qty</th>
                          <th>Đơn giá</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedLineItems.map((it, idx) => (
                          <tr key={`${idx}-${it?.name || 'item'}`}>
                            <td>{it?.name || it?.title || '-'}</td>
                            <td>{it?.qty ?? it?.quantity ?? '-'}</td>
                            <td>{formatMoney(it?.unit_price ?? it?.price ?? '-')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <form onSubmit={createPayment} style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 600, marginBottom: 6 }}>Tạo thanh toán</div>
                <div className="row" style={{ flexWrap: 'wrap' }}>
                  <input
                    placeholder="Số tiền"
                    type="number"
                    step="0.01"
                    value={payAmount}
                    onChange={(e) => setPayAmount(e.target.value)}
                    required
                    style={{ width: 160 }}
                  />
                  <select value={payMethod} onChange={(e) => setPayMethod(e.target.value)} style={{ width: 160 }}>
                    <option value="cash">cash</option>
                    <option value="card">card</option>
                    <option value="bank_transfer">bank_transfer</option>
                    <option value="qr">qr</option>
                    <option value="wallet">wallet</option>
                    <option value="other">other</option>
                  </select>
                  <input
                    placeholder="reference_code (tùy chọn)"
                    value={payReferenceCode}
                    onChange={(e) => setPayReferenceCode(e.target.value)}
                    style={{ width: 220 }}
                  />
                  <button className="btn" type="submit" disabled={creatingPayment}>
            {creatingPayment ? 'Đang tạo...' : 'Tạo thanh toán'}
          </button>
                </div>
              </form>

              <form onSubmit={refundInvoice} style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Hoan tien (refund)</div>
                <div className="row" style={{ flexWrap: 'wrap' }}>
                  <input
                    placeholder="Số tiền"
                    type="number"
                    step="0.01"
                    value={refundAmount}
                    onChange={(e) => setRefundAmount(e.target.value)}
                    required
                    style={{ width: 160 }}
                  />
                  <select value={refundMethod} onChange={(e) => setRefundMethod(e.target.value)} style={{ width: 160 }}>
                    <option value="cash">cash</option>
                    <option value="card">card</option>
                    <option value="bank_transfer">bank_transfer</option>
                    <option value="qr">qr</option>
                    <option value="wallet">wallet</option>
                    <option value="other">other</option>
                  </select>
                  <input
                    placeholder="reference_code (tùy chọn)"
                    value={refundReferenceCode}
                    onChange={(e) => setRefundReferenceCode(e.target.value)}
                    style={{ width: 220 }}
                  />
                  <button className="btn" type="submit" disabled={creatingRefund}>
              {creatingRefund ? 'Đang tạo...' : 'Hoàn tiền'}
            </button>
                </div>
              </form>

              <div style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Payments</div>
                {payments.length === 0 ? (
                  <div style={{ color: 'var(--muted)' }}>{paymentsLoading ? 'Đang tải...' : 'Chưa có thanh toán'}</div>
                ) : (
                  <div className="table-wrap" style={{ marginTop: 0 }}>
                    <table className="table dense">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Amount</th>
                          <th>Method</th>
                          <th>Ngày</th>
                        </tr>
                      </thead>
                      <tbody>
                        {payments.map((p) => (
                          <tr key={p.id || `${p.invoice_id}-${p.created_at}-${p.amount}`}>
                            <td>{p.id || '-'}</td>
                            <td>{formatMoney(p.amount)}</td>
                            <td>{p.method || '-'}</td>
                            <td>
                              {String(p.paid_at || p.created_at || '').replace('T', ' ').slice(0, 16) || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
