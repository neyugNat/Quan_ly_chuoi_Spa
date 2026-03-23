import { useEffect } from 'react'

export function Drawer({ open, title, onClose, children }) {
  useEffect(() => {
    if (!open) return

    function onKeyDown(e) {
      if (e.key === 'Escape') onClose?.()
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [open])

  if (!open) return null

  return (
    <>
      <div className="drawer-overlay" onClick={() => onClose?.()} aria-hidden="true" />
      <aside className="drawer" role="dialog" aria-modal="true">
        <div className="drawer-head">
          <div className="drawer-title">{title}</div>
          <button className="btn btn-sm btn-ghost" type="button" onClick={() => onClose?.()} aria-label="Đóng">
            Đóng
          </button>
        </div>
        <div className="drawer-body">{children}</div>
      </aside>
    </>
  )
}
