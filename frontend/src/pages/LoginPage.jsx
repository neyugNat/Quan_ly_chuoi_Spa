import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.tsx'
import { Sun, Moon, Laptop, Sparkles } from 'lucide-react'
import { apiFetch } from '../lib/api'

const CUSTOMER_VIEWS = new Set(['login', 'register', 'forgot', 'reset'])

const CUSTOMER_ERROR_MAP = {
  missing_fields: 'Vui lòng nhập đầy đủ thông tin.',
  missing_email: 'Vui lòng nhập email.',
  missing_credentials: 'Vui lòng nhập email và mật khẩu.',
  weak_password: 'Mật khẩu cần tối thiểu 6 ký tự.',
  email_exists: 'Email đã tồn tại, hãy đăng nhập hoặc quên mật khẩu.',
  customer_account_exists: 'Khách hàng này đã có tài khoản.',
  invalid_credentials: 'Email hoặc mật khẩu không đúng.',
  invalid_token: 'Token đặt lại mật khẩu không hợp lệ.',
  expired_token: 'Token đã hết hạn, vui lòng gửi lại yêu cầu.',
  customer_inactive: 'Tài khoản khách hàng chưa hoạt động.',
  account_inactive: 'Tài khoản đang bị khóa.',
  mail_send_failed: 'Không gửi được email. Vui lòng kiểm tra SMTP.',
  missing_branch: 'Hệ thống chưa có chi nhánh để tạo tài khoản.',
}

const inputClass =
  'w-full px-4 py-3 bg-gray-50/50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-gray-800 dark:text-gray-200'

function normalizeCustomerView(rawValue) {
  const value = String(rawValue || '').trim().toLowerCase()
  return CUSTOMER_VIEWS.has(value) ? value : 'login'
}

function subtitleForCustomer(view) {
  if (view === 'register') return 'Tạo tài khoản khách hàng để đặt lịch online'
  if (view === 'forgot') return 'Nhập email để nhận link đặt lại mật khẩu'
  if (view === 'reset') return 'Đặt mật khẩu mới cho tài khoản khách hàng'
  return 'Đăng nhập khách hàng để đặt lịch'
}

function toUiError(err, fallback = 'Có lỗi xảy ra, vui lòng thử lại.') {
  const code = err?.data?.error
  return CUSTOMER_ERROR_MAP[code] || fallback
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { colorMode, setColorMode, isDark } = useTheme()
  const [searchParams] = useSearchParams()

  const initialMode = searchParams.get('mode') === 'customer' ? 'customer' : 'staff'
  const initialCustomerView = normalizeCustomerView(searchParams.get('view'))
  const initialResetToken = (searchParams.get('token') || '').trim()

  const [mode, setMode] = useState(initialMode)
  const [customerView, setCustomerView] = useState(
    initialMode === 'customer'
      ? (initialResetToken ? 'reset' : initialCustomerView)
      : 'login',
  )

  const [staffUsername, setStaffUsername] = useState('')
  const [staffPassword, setStaffPassword] = useState('')

  const [customerEmail, setCustomerEmail] = useState('')
  const [customerPassword, setCustomerPassword] = useState('')

  const [registerName, setRegisterName] = useState('')
  const [registerPhone, setRegisterPhone] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [registerPasswordConfirm, setRegisterPasswordConfirm] = useState('')

  const [forgotEmail, setForgotEmail] = useState('')
  const [resetToken, setResetToken] = useState(initialResetToken)
  const [resetPassword, setResetPassword] = useState('')
  const [resetPasswordConfirm, setResetPasswordConfirm] = useState('')

  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false)

  function clearMessages() {
    setError('')
    setNotice('')
  }

  function switchMode(nextMode) {
    setMode(nextMode)
    clearMessages()
  }

  function switchCustomerView(nextView) {
    setCustomerView(nextView)
    clearMessages()
  }

  function persistCustomerSession(result) {
    const token = result?.token
    const customer = result?.account?.customer || null
    if (token) localStorage.setItem('customer_token', token)
    if (customer) localStorage.setItem('customer_profile', JSON.stringify(customer))
  }

  async function onStaffSubmit(e) {
    e.preventDefault()
    clearMessages()
    setLoading(true)
    try {
      await login(staffUsername, staffPassword)
      navigate('/', { replace: true })
    } catch (err) {
      const msg = err?.data?.error || 'login_failed'
      setError(String(msg))
    } finally {
      setLoading(false)
    }
  }

  async function onCustomerLoginSubmit(e) {
    e.preventDefault()
    clearMessages()
    setLoading(true)
    try {
      const result = await apiFetch('/api/customer-auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: customerEmail, password: customerPassword }),
      })
      persistCustomerSession(result)
      setNotice('Đăng nhập khách hàng thành công. Bước tiếp theo có thể mở cổng đặt lịch.')
    } catch (err) {
      setError(toUiError(err, 'Đăng nhập khách hàng thất bại.'))
    } finally {
      setLoading(false)
    }
  }

  async function onCustomerRegisterSubmit(e) {
    e.preventDefault()
    clearMessages()

    if (registerPassword !== registerPasswordConfirm) {
      setError('Mật khẩu xác nhận không khớp.')
      return
    }

    setLoading(true)
    try {
      const result = await apiFetch('/api/customer-auth/register', {
        method: 'POST',
        body: JSON.stringify({
          full_name: registerName,
          phone: registerPhone,
          email: registerEmail,
          password: registerPassword,
        }),
      })
      persistCustomerSession(result)
      setCustomerEmail(registerEmail)
      setCustomerPassword('')
      switchCustomerView('login')
      setNotice('Tạo tài khoản thành công. Bạn có thể đăng nhập ngay.')
    } catch (err) {
      setError(toUiError(err, 'Tạo tài khoản thất bại.'))
    } finally {
      setLoading(false)
    }
  }

  async function onCustomerForgotSubmit(e) {
    e.preventDefault()
    clearMessages()
    setLoading(true)
    try {
      const result = await apiFetch('/api/customer-auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email: forgotEmail }),
      })
      if (result?.reset_token) {
        setResetToken(result.reset_token)
        switchCustomerView('reset')
        setNotice(`Đã tạo token reset (dev mode): ${result.reset_token}`)
      } else {
        setNotice('Nếu email tồn tại, hệ thống đã gửi link đặt lại mật khẩu.')
      }
    } catch (err) {
      setError(toUiError(err, 'Không thể gửi yêu cầu đặt lại mật khẩu.'))
    } finally {
      setLoading(false)
    }
  }

  async function onCustomerResetSubmit(e) {
    e.preventDefault()
    clearMessages()

    if (resetPassword !== resetPasswordConfirm) {
      setError('Mật khẩu xác nhận không khớp.')
      return
    }

    setLoading(true)
    try {
      await apiFetch('/api/customer-auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ token: resetToken, new_password: resetPassword }),
      })
      setCustomerPassword('')
      switchCustomerView('login')
      setNotice('Đặt lại mật khẩu thành công. Bạn hãy đăng nhập lại.')
    } catch (err) {
      setError(toUiError(err, 'Đặt lại mật khẩu thất bại.'))
    } finally {
      setLoading(false)
    }
  }

  const getModeIcon = (modeStr) => {
    if (modeStr === 'light') return <Sun size={20} className="text-amber-500" />
    if (modeStr === 'dark') return <Moon size={20} className="text-indigo-400" />
    return <Laptop size={20} className="text-slate-400" />
  }

  const handleSelectMode = (m) => {
    setColorMode(m)
    setIsThemeMenuOpen(false)
  }

  const pageBgImage = isDark ? "url('/spa_bg_dark.png')" : "url('/spa_bg_light.png')"
  const subtitle =
    mode === 'staff'
      ? 'Đăng nhập nhân sự Lotus Spa Management'
      : subtitleForCustomer(customerView)

  return (
    <div
      className="min-h-screen flex items-center justify-center relative bg-cover bg-center transition-all duration-700"
      style={{ backgroundImage: pageBgImage }}
    >
      <div className="absolute inset-0 bg-white/30 dark:bg-black/60 backdrop-blur-sm transition-colors duration-700" />

      <div className="relative z-10 w-full max-w-md p-6 mx-4">
        <div className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/50 dark:border-gray-800/50 p-8">
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-indigo-500/30">
              <Sparkles size={32} className="text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">Chào mừng trở lại</h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">{subtitle}</p>
          </div>

          <div className="mb-5 p-1 bg-gray-100/80 dark:bg-gray-800/80 rounded-xl grid grid-cols-2 gap-1">
            <button
              type="button"
              onClick={() => switchMode('staff')}
              className={`py-2 text-sm rounded-lg transition-colors ${
                mode === 'staff'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              Nhân sự
            </button>
            <button
              type="button"
              onClick={() => {
                switchMode('customer')
                if (customerView === 'login') return
                switchCustomerView(initialResetToken ? 'reset' : 'login')
              }}
              className={`py-2 text-sm rounded-lg transition-colors ${
                mode === 'customer'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              Khách hàng
            </button>
          </div>

          {mode === 'staff' ? (
            <form onSubmit={onStaffSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5" htmlFor="username">
                  Tài khoản
                </label>
                <input
                  id="username"
                  className={inputClass}
                  autoComplete="username"
                  placeholder="Nhập tên đăng nhập"
                  value={staffUsername}
                  onChange={(e) => setStaffUsername(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5" htmlFor="password">
                  Mật khẩu
                </label>
                <input
                  id="password"
                  type="password"
                  className={inputClass}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={staffPassword}
                  onChange={(e) => setStaffPassword(e.target.value)}
                />
              </div>

              {error && (
                <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm p-3 rounded-xl border border-red-100 dark:border-red-900/50">
                  {error}
                </div>
              )}

              <button
                disabled={loading}
                type="submit"
                className="w-full py-3.5 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white rounded-xl font-medium shadow-lg shadow-indigo-500/30 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70 disabled:hover:scale-100"
              >
                {loading ? 'Đang xác thực...' : 'Đăng nhập nhân sự'}
              </button>
            </form>
          ) : (
            <>
              {customerView === 'login' && (
                <form onSubmit={onCustomerLoginSubmit} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5" htmlFor="customer-email">
                      Email
                    </label>
                    <input
                      id="customer-email"
                      type="email"
                      className={inputClass}
                      autoComplete="email"
                      placeholder="Nhập email"
                      value={customerEmail}
                      onChange={(e) => setCustomerEmail(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5" htmlFor="customer-password">
                      Mật khẩu
                    </label>
                    <input
                      id="customer-password"
                      type="password"
                      className={inputClass}
                      autoComplete="current-password"
                      placeholder="••••••••"
                      value={customerPassword}
                      onChange={(e) => setCustomerPassword(e.target.value)}
                    />
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <button type="button" onClick={() => switchCustomerView('register')} className="text-indigo-600 dark:text-indigo-300 hover:underline">
                      Tạo tài khoản
                    </button>
                    <button type="button" onClick={() => switchCustomerView('forgot')} className="text-sky-600 dark:text-sky-300 hover:underline">
                      Quên mật khẩu?
                    </button>
                  </div>

                  {error && (
                    <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm p-3 rounded-xl border border-red-100 dark:border-red-900/50">
                      {error}
                    </div>
                  )}
                  {notice && (
                    <div className="bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-sm p-3 rounded-xl border border-emerald-100 dark:border-emerald-900/50">
                      {notice}
                    </div>
                  )}

                  <button
                    disabled={loading}
                    type="submit"
                    className="w-full py-3.5 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 text-white rounded-xl font-medium shadow-lg shadow-sky-500/30 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70 disabled:hover:scale-100"
                  >
                    {loading ? 'Đang xác thực...' : 'Đăng nhập khách hàng'}
                  </button>
                </form>
              )}

              {customerView === 'register' && (
                <form onSubmit={onCustomerRegisterSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5" htmlFor="register-name">
                      Họ và tên
                    </label>
                    <input id="register-name" className={inputClass} value={registerName} onChange={(e) => setRegisterName(e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5" htmlFor="register-phone">
                      Số điện thoại (không bắt buộc)
                    </label>
                    <input id="register-phone" className={inputClass} value={registerPhone} onChange={(e) => setRegisterPhone(e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5" htmlFor="register-email">
                      Email
                    </label>
                    <input id="register-email" type="email" className={inputClass} value={registerEmail} onChange={(e) => setRegisterEmail(e.target.value)} />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <input
                      type="password"
                      className={inputClass}
                      placeholder="Mật khẩu"
                      value={registerPassword}
                      onChange={(e) => setRegisterPassword(e.target.value)}
                    />
                    <input
                      type="password"
                      className={inputClass}
                      placeholder="Xác nhận mật khẩu"
                      value={registerPasswordConfirm}
                      onChange={(e) => setRegisterPasswordConfirm(e.target.value)}
                    />
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <button type="button" onClick={() => switchCustomerView('login')} className="text-indigo-600 dark:text-indigo-300 hover:underline">
                      Quay lại đăng nhập
                    </button>
                  </div>

                  {error && (
                    <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm p-3 rounded-xl border border-red-100 dark:border-red-900/50">
                      {error}
                    </div>
                  )}
                  {notice && (
                    <div className="bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-sm p-3 rounded-xl border border-emerald-100 dark:border-emerald-900/50">
                      {notice}
                    </div>
                  )}

                  <button
                    disabled={loading}
                    type="submit"
                    className="w-full py-3.5 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white rounded-xl font-medium shadow-lg shadow-emerald-500/30 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70 disabled:hover:scale-100"
                  >
                    {loading ? 'Đang tạo tài khoản...' : 'Tạo tài khoản'}
                  </button>
                </form>
              )}

              {customerView === 'forgot' && (
                <form onSubmit={onCustomerForgotSubmit} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5" htmlFor="forgot-email">
                      Email tài khoản
                    </label>
                    <input id="forgot-email" type="email" className={inputClass} value={forgotEmail} onChange={(e) => setForgotEmail(e.target.value)} />
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <button type="button" onClick={() => switchCustomerView('login')} className="text-indigo-600 dark:text-indigo-300 hover:underline">
                      Quay lại đăng nhập
                    </button>
                  </div>

                  {error && (
                    <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm p-3 rounded-xl border border-red-100 dark:border-red-900/50">
                      {error}
                    </div>
                  )}
                  {notice && (
                    <div className="bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-sm p-3 rounded-xl border border-emerald-100 dark:border-emerald-900/50">
                      {notice}
                    </div>
                  )}

                  <button
                    disabled={loading}
                    type="submit"
                    className="w-full py-3.5 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 text-white rounded-xl font-medium shadow-lg shadow-sky-500/30 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70 disabled:hover:scale-100"
                  >
                    {loading ? 'Đang gửi...' : 'Gửi email đặt lại mật khẩu'}
                  </button>
                </form>
              )}

              {customerView === 'reset' && (
                <form onSubmit={onCustomerResetSubmit} className="space-y-4">
                  <input
                    className={inputClass}
                    placeholder="Token đặt lại mật khẩu"
                    value={resetToken}
                    onChange={(e) => setResetToken(e.target.value)}
                  />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <input
                      type="password"
                      className={inputClass}
                      placeholder="Mật khẩu mới"
                      value={resetPassword}
                      onChange={(e) => setResetPassword(e.target.value)}
                    />
                    <input
                      type="password"
                      className={inputClass}
                      placeholder="Xác nhận mật khẩu"
                      value={resetPasswordConfirm}
                      onChange={(e) => setResetPasswordConfirm(e.target.value)}
                    />
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <button type="button" onClick={() => switchCustomerView('login')} className="text-indigo-600 dark:text-indigo-300 hover:underline">
                      Quay lại đăng nhập
                    </button>
                  </div>

                  {error && (
                    <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm p-3 rounded-xl border border-red-100 dark:border-red-900/50">
                      {error}
                    </div>
                  )}
                  {notice && (
                    <div className="bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-sm p-3 rounded-xl border border-emerald-100 dark:border-emerald-900/50">
                      {notice}
                    </div>
                  )}

                  <button
                    disabled={loading}
                    type="submit"
                    className="w-full py-3.5 bg-gradient-to-r from-indigo-500 to-blue-600 hover:from-indigo-600 hover:to-blue-700 text-white rounded-xl font-medium shadow-lg shadow-indigo-500/30 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70 disabled:hover:scale-100"
                  >
                    {loading ? 'Đang cập nhật...' : 'Lưu mật khẩu mới'}
                  </button>
                </form>
              )}
            </>
          )}
        </div>
      </div>

      <div className="absolute bottom-6 right-6 z-50 flex flex-col items-center gap-2">
        <div
          className={`flex flex-col gap-2 transition-all duration-300 origin-bottom ${
            isThemeMenuOpen ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-95 translate-y-4 pointer-events-none'
          }`}
        >
          {['light', 'dark', 'system']
            .filter((m) => m !== colorMode)
            .map((m) => (
            <div key={m} className="relative group/item flex justify-center">
              <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 bg-white/80 dark:bg-gray-800/80 backdrop-blur-md px-3 py-1.5 rounded-full shadow-sm border border-gray-200/50 dark:border-gray-700/50 text-xs font-medium text-gray-500 dark:text-gray-400 opacity-0 group-hover/item:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                {m === 'light' ? 'Sáng' : m === 'dark' ? 'Tối' : 'Hệ thống'}
              </div>
              <button
                onClick={() => handleSelectMode(m)}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all bg-white/90 dark:bg-gray-800/90 backdrop-blur-md shadow-md hover:scale-110 active:scale-95 border border-white/50 dark:border-gray-700 hover:border-indigo-300 outline-none"
              >
                {getModeIcon(m)}
              </button>
            </div>
          ))}
        </div>

        <div className="relative group">
          <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 bg-white/80 dark:bg-gray-800/80 backdrop-blur-md px-3 py-1.5 rounded-full shadow-sm border border-gray-200/50 dark:border-gray-700/50 text-xs font-medium text-gray-500 dark:text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
             {isThemeMenuOpen ? (colorMode === 'light' ? 'Sáng' : colorMode === 'dark' ? 'Tối' : 'Hệ thống') : 'Giao diện'}
          </div>
          <button
            onClick={() => setIsThemeMenuOpen(!isThemeMenuOpen)}
            className="w-12 h-12 bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl rounded-full shadow-xl border border-white/50 dark:border-gray-700 flex items-center justify-center hover:scale-110 active:scale-95 transition-all outline-none"
          >
            {getModeIcon(colorMode)}
          </button>
        </div>
      </div>
    </div>
  )
}
