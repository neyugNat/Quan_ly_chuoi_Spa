import { useState } from "react";
import { Outlet, NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, CalendarDays, Users, Sparkles,
  UserCheck, MapPin, BarChart3, ChevronLeft, ChevronRight,
  Bell, Search, LogOut, Settings, Menu, ChevronDown,
  ShieldCheck, Package, ScrollText,
} from "lucide-react";
import lotusLogo from "../assets/lotus-logo.svg";
import { useTheme, wallpapers } from "../context/ThemeContext";
import { useAuth } from "../auth/AuthContext";
import { canSeeRoles } from "../auth/navConfig";

const navGroups = [
  {
    label: "Menu chính",
    items: [
      { to: "/dashboard", label: "Tổng quan", icon: LayoutDashboard, exact: true, roles: ['super_admin', 'branch_manager'] },
      { to: "/appointments", label: "Lịch hẹn", icon: CalendarDays, roles: ['super_admin', 'branch_manager', 'reception'] },
      { to: "/customers", label: "Khách hàng", icon: Users, roles: ['super_admin', 'branch_manager', 'reception', 'cashier'] },
      { to: "/services", label: "Dịch vụ", icon: Sparkles, roles: ['super_admin', 'branch_manager'] },
      { to: "/hr", label: "Nhân viên", icon: UserCheck, roles: ['super_admin', 'branch_manager'] },
      { to: "/branches", label: "Chi nhánh", icon: MapPin, roles: ['super_admin'] },
      { to: "/reports", label: "Báo cáo", icon: BarChart3, roles: ['super_admin', 'branch_manager'] },
    ],
  },
  {
    label: "Quản trị hệ thống",
    items: [
      { to: "/users", label: "Tài khoản", icon: ShieldCheck, roles: ['super_admin'] },
      { to: "/inventory", label: "Kho vật dụng", icon: Package, roles: ['super_admin', 'branch_manager', 'warehouse'] },
      { to: "/audit-logs", label: "Nhật ký hệ thống", icon: ScrollText, roles: ['super_admin'] },
    ],
  },
];

const allItems = navGroups.flatMap(g => g.items);

const pageTitles: Record<string, string> = {
  "/settings": "Cài đặt",
  "/accounts": "Tài khoản",
  "/inventory": "Kho vật dụng",
  "/logs": "Nhật ký hệ thống",
};

export function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, wallpaper, isDark } = useTheme();
  const { user: _user, logout } = useAuth();
  const user = _user as any;

  const currentPage = allItems.find((item) =>
    (item as any).exact ? location.pathname === item.to : location.pathname.startsWith(item.to)
  );
  const pageTitle = currentPage?.label || pageTitles[location.pathname] || "Tổng quan";

  const activeWallpaper = wallpapers.find((w) => w.id === wallpaper);

  const isActive = (item: { to: string; exact?: boolean }) =>
    item.exact ? location.pathname === item.to : location.pathname.startsWith(item.to);

  // Dark mode: use very dark background instead of light theme gradient
  const pageBg = isDark
    ? "linear-gradient(135deg, #101a31 0%, #14203a 52%, #172744 100%)"
    : theme.bg;

  // Dark mode: darken sidebar a bit via filter
  const sidebarStyle = isDark
    ? { background: theme.sidebar, filter: "brightness(0.88)" }
    : { background: theme.sidebar };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: pageBg }}>
      {activeWallpaper && activeWallpaper.id !== "none" && (
        <div className="fixed inset-0 pointer-events-none z-0 opacity-15" style={activeWallpaper.style} />
      )}

      {mobileOpen && (
        <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar - always dark gradient, force white text */}
      <aside
        className={`
          fixed md:relative z-40 h-full flex flex-col
          transition-all duration-300 ease-in-out shadow-2xl
          ${collapsed ? "w-[72px]" : "w-[240px]"}
          ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
        style={{ ...sidebarStyle, color: "white" }}
      >
        <div className="absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl opacity-20 pointer-events-none"
          style={{ background: "radial-gradient(circle, rgba(255,255,255,0.4) 0%, transparent 70%)" }} />
        <div className="absolute bottom-20 left-0 w-24 h-24 rounded-full blur-3xl opacity-15 pointer-events-none"
          style={{ background: "radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%)" }} />

        {/* Logo */}
        <div className={`relative flex items-center gap-2.5 py-4 border-b border-white/10 ${collapsed ? "px-3 justify-center" : "px-4"}`}>
          <div className="w-10 h-10 rounded-xl bg-white/15 backdrop-blur flex items-center justify-center flex-shrink-0 overflow-hidden ring-1 ring-white/20 shadow-lg">
            <img src={lotusLogo} alt="Lotus Spa" className="w-9 h-9 object-contain" />
          </div>
          {!collapsed && (
            <div>
              <div className="text-white font-semibold text-sm tracking-wide drop-shadow-sm">Lotus Spa</div>
              <div className="text-white/50 text-xs tracking-widest uppercase" style={{ fontSize: "9px" }}>Management</div>
            </div>
          )}
        </div>

        {/* Nav groups */}
        <nav className="flex-1 py-3 px-3 overflow-y-auto space-y-4">
          {navGroups.map((group) => {
            const allowedItems = group.items.filter(item => canSeeRoles(user?.roles, item.roles));
            if (allowedItems.length === 0) return null;
            return (
            <div key={group.label}>
              {!collapsed && (
                <div className="px-2 pb-2">
                  <span className="text-white/30 text-xs font-semibold uppercase tracking-widest" style={{ fontSize: "10px" }}>{group.label}</span>
                </div>
              )}
              {collapsed && <div className="border-t border-white/10 mb-2" />}
              <div className="space-y-0.5">
                {allowedItems.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item as any);
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileOpen(false)}
                      className={`
                        relative flex items-center gap-3 px-3 py-2.5 rounded-xl
                        transition-all duration-200 group overflow-hidden
                        ${active ? "bg-white/20 text-white shadow-md" : "text-white/60 hover:bg-white/10 hover:text-white"}
                      `}
                      style={active ? { boxShadow: "0 4px 20px rgba(255,255,255,0.1), inset 0 1px 0 rgba(255,255,255,0.2)" } : {}}
                    >
                      {active && (
                        <span className="absolute inset-0 rounded-xl opacity-60"
                          style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.05) 100%)" }} />
                      )}
                      {active && (
                        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full bg-white shadow-glow" />
                      )}
                      <Icon size={17} className={`flex-shrink-0 relative z-10 transition-transform duration-200
                        ${active ? "text-white" : "text-white/60 group-hover:text-white group-hover:scale-110"}`} />
                      {!collapsed && <span className="text-sm font-medium truncate relative z-10">{item.label}</span>}
                      <span className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                        style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.08) 0%, transparent 100%)" }} />
                    </NavLink>
                  );
                })}
              </div>
            </div>
          )})}
        </nav>

        {/* Settings & Logout */}
        <div className="p-3 border-t border-white/10 space-y-0.5">
          <button
            onClick={() => { navigate("/settings"); setMobileOpen(false); }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative overflow-hidden
              ${location.pathname === "/settings" ? "bg-white/20 text-white shadow-md" : "text-white/60 hover:bg-white/10 hover:text-white"}`}
          >
            {location.pathname === "/settings" && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full bg-white" />
            )}
            <Settings size={17} className="flex-shrink-0 group-hover:rotate-45 transition-transform duration-300" />
            {!collapsed && <span className="text-sm font-medium">Cài đặt</span>}
          </button>
          <button onClick={logout} className="cursor-pointer w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-white/60 hover:bg-red-500/20 hover:text-red-300 transition-all duration-200 group">
            <LogOut size={17} className="flex-shrink-0 group-hover:-translate-x-1 transition-transform duration-200" />
            {!collapsed && <span className="text-sm font-medium">Đăng xuất</span>}
          </button>
        </div>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden md:flex absolute -right-3 top-20 w-6 h-6 rounded-full text-white items-center justify-center shadow-lg transition-transform duration-200 hover:scale-110"
          style={{ background: theme.accent }}
        >
          {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
        </button>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0 relative z-10">
        <header className="h-16 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-white/50 dark:border-gray-700/50 flex items-center justify-between px-4 md:px-6 flex-shrink-0 shadow-sm">
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileOpen(true)} className="md:hidden p-2 rounded-lg hover:bg-white/70 text-gray-500 dark:text-gray-300">
              <Menu size={20} />
            </button>
            <div>
              <h1 className="text-gray-800 dark:text-gray-100 text-base">{pageTitle}</h1>
              <p className="text-gray-400 dark:text-gray-500 text-xs hidden sm:block">Thứ Sáu, 27 tháng 3, 2026</p>
            </div>
          </div>

          <div className="flex items-center gap-2 md:gap-3">
            <div className="hidden sm:flex items-center gap-2 bg-white/60 dark:bg-gray-800/60 border border-gray-200/60 dark:border-gray-600/60 rounded-xl px-3 py-2 backdrop-blur-sm">
              <Search size={14} className="text-gray-400 flex-shrink-0" />
              <input type="text" placeholder="Tìm kiếm..."
                className="bg-transparent text-sm text-gray-700 dark:text-gray-200 placeholder-gray-400 outline-none w-36 md:w-48" />
            </div>
            <button className="relative p-2.5 rounded-xl hover:bg-white/70 dark:hover:bg-gray-700/70 transition-colors group">
              <Bell size={18} className="text-gray-500 dark:text-gray-300 group-hover:animate-pulse" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-400 border-2 border-white dark:border-gray-900 animate-pulse" />
            </button>
            <div className="flex items-center gap-2.5 pl-3 border-l border-gray-200/60 dark:border-gray-600/60 cursor-pointer">
              <div className="w-8 h-8 rounded-full ring-2 ring-offset-1 overflow-hidden shadow-sm" style={{ outlineColor: theme.accent }}>
                <img src={lotusLogo} alt="Lotus Spa" className="w-full h-full object-contain bg-gradient-to-br from-violet-100 to-blue-100" />
              </div>
              <div className="hidden md:block">
                <div className="text-xs font-semibold text-gray-800 dark:text-gray-100 leading-tight">{user?.username}</div>
                <div className="text-xs text-gray-400">Người dùng</div>
              </div>
              <ChevronDown size={14} className="text-gray-400 hidden md:block" />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-6 relative bg-transparent">
          <Outlet />
        </main>
      </div>
    </div>
  );
}