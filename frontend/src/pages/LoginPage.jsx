import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.tsx'
import { Sun, Moon, Laptop, Sparkles } from 'lucide-react'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { colorMode, setColorMode, isDark, theme } = useTheme()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/', { replace: true })
    } catch (err) {
      const msg = err?.data?.error || 'login_failed'
      setError(String(msg))
    } finally {
      setLoading(false)
    }
  }

  const getModeIcon = (modeStr) => {
    if (modeStr === "light") return <Sun size={20} className="text-amber-500" />;
    if (modeStr === "dark") return <Moon size={20} className="text-indigo-400" />;
    return <Laptop size={20} className="text-slate-400" />;
  };

  const handleSelectMode = (m) => {
    setColorMode(m);
    setIsThemeMenuOpen(false);
  };

  const pageBgImage = isDark ? "url('/spa_bg_dark.png')" : "url('/spa_bg_light.png')";

  return (
    <div 
      className="min-h-screen flex items-center justify-center relative bg-cover bg-center transition-all duration-700"
      style={{ backgroundImage: pageBgImage }}
    >
      
      {/* Overlay to ensure the form remains highly readable and pops out against the background */}
      <div className="absolute inset-0 bg-white/30 dark:bg-black/60 backdrop-blur-sm transition-colors duration-700" />

      {/* Login Card */}
      <div className="relative z-10 w-full max-w-md p-6 mx-4">
        <div className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/50 dark:border-gray-800/50 p-8">
          
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-indigo-500/30">
              <Sparkles size={32} className="text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">Chào mừng trở lại</h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Đăng nhập vào Lotus Spa Management</p>
          </div>

          <form onSubmit={onSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5" htmlFor="username">
                Tài khoản
              </label>
              <input
                id="username"
                className="w-full px-4 py-3 bg-gray-50/50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-gray-800 dark:text-gray-200"
                autoComplete="username"
                placeholder="Nhập tên đăng nhập"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5" htmlFor="password">
                Mật khẩu
              </label>
              <input
                id="password"
                type="password"
                className="w-full px-4 py-3 bg-gray-50/50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-gray-800 dark:text-gray-200"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
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
              {loading ? 'Đang xác thực...' : 'Đăng nhập'}
            </button>
          </form>
        </div>
      </div>

      {/* Floating Theme Toggle Stack (Bottom Right) */}
      <div className="absolute bottom-6 right-6 z-50 flex flex-col items-center gap-2">
        {/* The Stacked Options */}
        <div 
          className={`flex flex-col gap-2 transition-all duration-300 origin-bottom ${
            isThemeMenuOpen ? "opacity-100 scale-100 translate-y-0" : "opacity-0 scale-95 translate-y-4 pointer-events-none"
          }`}
        >
          {["light", "dark", "system"]
            .filter(m => m !== colorMode)
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

        {/* The Main Toggle Button */}
        <div className="relative group">
          <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 bg-white/80 dark:bg-gray-800/80 backdrop-blur-md px-3 py-1.5 rounded-full shadow-sm border border-gray-200/50 dark:border-gray-700/50 text-xs font-medium text-gray-500 dark:text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
             {isThemeMenuOpen ? (colorMode === 'light' ? 'Sáng' : colorMode === 'dark' ? 'Tối' : 'Hệ thống') : "Giao diện"}
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
