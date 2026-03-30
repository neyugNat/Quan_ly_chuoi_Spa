import { useState } from "react";
import {
  Palette, Globe, Bell, Monitor, User, Lock, Database,
  Check, Sun, Moon, Laptop, Volume2, Mail,
  Smartphone, FileBarChart, ChevronRight, Save, RefreshCw,
} from "lucide-react";
import { useTheme, themes, wallpapers, languages } from "../../context/ThemeContext";
import { useAuth } from "../../auth/AuthContext";
import { apiFetch } from "../../lib/api";

const sections = [
  { id: "appearance", label: "Giao diện", icon: Palette },
  { id: "language", label: "Ngôn ngữ", icon: Globe },
  { id: "notifications", label: "Thông báo", icon: Bell },
  { id: "display", label: "Hiển thị", icon: Monitor },
  { id: "account", label: "Tài khoản", icon: User },
  { id: "security", label: "Bảo mật", icon: Lock },
  { id: "data", label: "Dữ liệu & Backup", icon: Database },
];

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-11 h-6 rounded-full transition-all duration-300 flex-shrink-0 ${checked ? "bg-violet-500" : "bg-gray-200"}`}
    >
      <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform duration-300 ${checked ? "translate-x-5" : "translate-x-0"}`} />
    </button>
  );
}

export function Settings() {
  const [activeSection, setActiveSection] = useState("appearance");
  const [saved, setSaved] = useState(false);
  const { user: _user } = useAuth();
  const user = _user as any;
  const {
    theme, setThemeId,
    wallpaper, setWallpaper,
    language, setLanguage,
    density, setDensity,
    notifications, setNotification,
    colorMode, setColorMode,
  } = useTheme();

  // Password change state
  const [pwOld, setPwOld] = useState("");
  const [pwNew, setPwNew] = useState("");
  const [pwConfirm, setPwConfirm] = useState("");
  const [pwMsg, setPwMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [pwLoading, setPwLoading] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleChangePassword = async () => {
    if (!pwNew || pwNew !== pwConfirm) {
      setPwMsg({ type: "err", text: "Mật khẩu mới không khớp!" });
      return;
    }
    if (pwNew.length < 6) {
      setPwMsg({ type: "err", text: "Mật khẩu phải có ít nhất 6 ký tự!" });
      return;
    }
    setPwLoading(true);
    setPwMsg(null);
    try {
      await apiFetch("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ old_password: pwOld, new_password: pwNew }),
      });
      setPwMsg({ type: "ok", text: "Đổi mật khẩu thành công!" });
      setPwOld(""); setPwNew(""); setPwConfirm("");
    } catch (err: any) {
      setPwMsg({ type: "err", text: err?.data?.error || "Đổi mật khẩu thất bại!" });
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-gray-500 text-sm">Tuỳ chỉnh giao diện, ngôn ngữ và hệ thống</p>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 px-3.5 py-2 border border-gray-200 rounded-xl text-xs font-semibold text-gray-500 hover:bg-gray-50 bg-white transition-colors">
            <RefreshCw size={13} /> Đặt lại mặc định
          </button>
          <button
            onClick={handleSave}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white shadow-md transition-all ${saved ? "bg-emerald-500" : "bg-gradient-to-r from-violet-500 to-indigo-500 hover:opacity-90"}`}
          >
            {saved ? <><Check size={13} /> Đã lưu!</> : <><Save size={13} /> Lưu cài đặt</>}
          </button>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-5">
        {/* Sidebar nav */}
        <div className="w-full lg:w-56 flex-shrink-0">
          <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 overflow-hidden">
            {sections.map((s) => {
              const Icon = s.icon;
              const isActive = activeSection === s.id;
              return (
                <button
                  key={s.id}
                  onClick={() => setActiveSection(s.id)}
                  className={`w-full flex items-center justify-between px-4 py-3 text-sm transition-all duration-200 group
                    ${isActive ? "bg-gradient-to-r from-violet-50 to-indigo-50 text-violet-700 font-semibold border-l-2 border-violet-500" : "text-gray-600 hover:bg-gray-50 border-l-2 border-transparent"}`}
                >
                  <span className="flex items-center gap-2.5">
                    <Icon size={16} className={isActive ? "text-violet-600" : "text-gray-400 group-hover:text-gray-600"} />
                    {s.label}
                  </span>
                  <ChevronRight size={13} className={`transition-transform ${isActive ? "rotate-90 text-violet-400" : "text-gray-300"}`} />
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 space-y-4">
          {/* ─── APPEARANCE ─── */}
          {activeSection === "appearance" && (
            <>
              {/* Color Theme */}
              <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-7 h-7 rounded-lg bg-violet-100 flex items-center justify-center">
                    <Palette size={14} className="text-violet-600" />
                  </div>
                  <div>
                    <h3 className="text-gray-800 text-sm">Bảng màu chủ đề</h3>
                    <p className="text-gray-400 text-xs">Chọn gam màu cho toàn bộ ứng dụng</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                  {themes.map((t) => {
                    const isSelected = theme.id === t.id;
                    return (
                      <button
                        key={t.id}
                        onClick={() => setThemeId(t.id)}
                        className={`relative flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all duration-200 hover:scale-105
                          ${isSelected ? "border-violet-500 shadow-lg" : "border-gray-100 hover:border-gray-200"}`}
                      >
                        {/* Preview */}
                        <div className="w-full h-14 rounded-lg overflow-hidden shadow-sm" style={{ background: t.bg }} />
                        <div className="w-full h-4 rounded-md" style={{ background: t.sidebar }} />
                        {isSelected && (
                          <span className="absolute top-2 right-2 w-5 h-5 bg-violet-500 rounded-full flex items-center justify-center shadow">
                            <Check size={10} className="text-white" />
                          </span>
                        )}
                        <span className="text-xs font-medium text-gray-600 truncate w-full text-center">{t.emoji} {t.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Wallpaper */}
              <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-7 h-7 rounded-lg bg-pink-100 flex items-center justify-center">
                    <Sun size={14} className="text-pink-600" />
                  </div>
                  <div>
                    <h3 className="text-gray-800 text-sm">Hình nền & Hiệu ứng</h3>
                    <p className="text-gray-400 text-xs">Lớp phủ gradient trên toàn trang</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {wallpapers.map((w) => {
                    const isSelected = wallpaper === w.id;
                    return (
                      <button
                        key={w.id}
                        onClick={() => setWallpaper(w.id)}
                        className={`relative flex flex-col items-center gap-2 p-2 rounded-xl border-2 transition-all duration-200 hover:scale-105
                          ${isSelected ? "border-violet-500 shadow-md" : "border-gray-100 hover:border-gray-200"}`}
                      >
                        <div className="w-full h-16 rounded-lg shadow-inner"
                          style={w.id === "none" ? { background: "#f9fafb", border: "1px dashed #d1d5db" } : w.style}
                        />
                        {isSelected && (
                          <span className="absolute top-2 right-2 w-5 h-5 bg-violet-500 rounded-full flex items-center justify-center shadow">
                            <Check size={10} className="text-white" />
                          </span>
                        )}
                        <span className="text-xs text-gray-600 font-medium truncate w-full text-center">{w.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Mode */}
              <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 dark:border-gray-700/60 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-7 h-7 rounded-lg bg-amber-100 flex items-center justify-center">
                    <Sun size={14} className="text-amber-600" />
                  </div>
                  <div>
                    <h3 className="text-gray-800 dark:text-gray-100 text-sm">Chế độ giao diện</h3>
                    <p className="text-gray-400 text-xs">Sáng, tối hoặc theo hệ thống</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  {([
                    { id: "light", label: "Sáng", icon: Sun, color: "text-amber-500", activeBg: "border-amber-400 bg-amber-50", activeText: "text-amber-700", activeDot: "bg-amber-400" },
                    { id: "dark",  label: "Tối",  icon: Moon, color: "text-indigo-500", activeBg: "border-indigo-400 bg-indigo-50", activeText: "text-indigo-700", activeDot: "bg-indigo-400" },
                    { id: "system", label: "Hệ thống", icon: Laptop, color: "text-slate-500", activeBg: "border-slate-400 bg-slate-50", activeText: "text-slate-700", activeDot: "bg-slate-400" },
                  ] as const).map((mode) => {
                    const Icon = mode.icon;
                    const isActive = colorMode === mode.id;
                    return (
                      <button
                        key={mode.id}
                        onClick={() => setColorMode(mode.id)}
                        className={`flex-1 flex flex-col items-center gap-2 py-4 rounded-xl border-2 transition-all duration-200 ${
                          isActive
                            ? mode.activeBg + " shadow-md scale-105"
                            : "border-gray-300 bg-white hover:border-gray-400 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700/50 dark:hover:bg-gray-700"
                        }`}
                      >
                        <Icon size={20} className={isActive ? mode.color : "text-gray-500 dark:text-gray-300"} />
                        <span className={`text-xs font-semibold ${isActive ? mode.activeText : "text-gray-600 dark:text-gray-300"}`}>{mode.label}</span>
                        {isActive && <span className={`w-2 h-2 rounded-full ${mode.activeDot}`} />}
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          {/* ─── LANGUAGE ─── */}
          {activeSection === "language" && (
            <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-7 h-7 rounded-lg bg-blue-100 flex items-center justify-center">
                  <Globe size={14} className="text-blue-600" />
                </div>
                <div>
                  <h3 className="text-gray-800 text-sm">Ngôn ngữ giao diện</h3>
                  <p className="text-gray-400 text-xs">Chọn ngôn ngữ hiển thị cho toàn bộ ứng dụng</p>
                </div>
              </div>
              <div className="space-y-2">
                {languages.map((lang) => {
                  const isSelected = language === lang.id;
                  return (
                    <button
                      key={lang.id}
                      onClick={() => setLanguage(lang.id)}
                      className={`w-full flex items-center justify-between px-4 py-3.5 rounded-xl border-2 transition-all duration-200
                        ${isSelected ? "border-violet-300 bg-violet-50" : "border-gray-100 hover:border-gray-200 hover:bg-gray-50"}`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{lang.flag}</span>
                        <div className="text-left">
                          <div className={`text-sm font-semibold ${isSelected ? "text-violet-700" : "text-gray-700"}`}>{lang.name}</div>
                          <div className="text-xs text-gray-400">{lang.id.toUpperCase()}</div>
                        </div>
                      </div>
                      {isSelected && (
                        <span className="w-6 h-6 bg-violet-500 rounded-full flex items-center justify-center">
                          <Check size={12} className="text-white" />
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              <div className="mt-5 p-4 bg-amber-50 border border-amber-100 rounded-xl">
                <p className="text-xs text-amber-700">💡 <strong>Ghi chú:</strong> Việc thay đổi ngôn ngữ sẽ áp dụng sau khi tải lại trang. Dữ liệu nhập liệu không bị ảnh hưởng.</p>
              </div>
            </div>
          )}

          {/* ─── NOTIFICATIONS ─── */}
          {activeSection === "notifications" && (
            <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-7 h-7 rounded-lg bg-red-100 flex items-center justify-center">
                  <Bell size={14} className="text-red-600" />
                </div>
                <div>
                  <h3 className="text-gray-800 text-sm">Cài đặt thông báo</h3>
                  <p className="text-gray-400 text-xs">Quản lý cách bạn nhận thông báo từ hệ thống</p>
                </div>
              </div>
              <div className="space-y-1">
                {[
                  { key: "email", icon: Mail, label: "Thông báo Email", desc: "Nhận email khi có lịch hẹn mới hoặc thay đổi", color: "text-blue-500" },
                  { key: "push", icon: Smartphone, label: "Thông báo đẩy", desc: "Thông báo trực tiếp trên trình duyệt", color: "text-green-500" },
                  { key: "sound", icon: Volume2, label: "Âm thanh thông báo", desc: "Phát âm khi có thông báo mới", color: "text-amber-500" },
                  { key: "reports", icon: FileBarChart, label: "Báo cáo tự động", desc: "Nhận báo cáo tổng hợp hàng tuần qua email", color: "text-purple-500" },
                ].map((item) => {
                  const Icon = item.icon;
                  const isOn = notifications[item.key as keyof typeof notifications];
                  return (
                    <div key={item.key} className="flex items-center justify-between p-4 rounded-xl hover:bg-gray-50 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-xl bg-gray-50 flex items-center justify-center`}>
                          <Icon size={16} className={item.color} />
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-gray-700">{item.label}</div>
                          <div className="text-xs text-gray-400">{item.desc}</div>
                        </div>
                      </div>
                      <Toggle
                        checked={isOn}
                        onChange={(v) => setNotification(item.key, v)}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ─── DISPLAY ─── */}
          {activeSection === "display" && (
            <>
              <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
                <div className="flex items-center gap-2 mb-5">
                  <div className="w-7 h-7 rounded-lg bg-cyan-100 flex items-center justify-center">
                    <Monitor size={14} className="text-cyan-600" />
                  </div>
                  <div>
                    <h3 className="text-gray-800 text-sm">Mật độ hiển thị</h3>
                    <p className="text-gray-400 text-xs">Điều chỉnh khoảng cách giữa các phần tử</p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: "compact", label: "Gọn", desc: "Nhiều thông tin hơn", icon: "▤" },
                    { id: "comfortable", label: "Chuẩn", desc: "Cân bằng mặc định", icon: "▥" },
                    { id: "spacious", label: "Rộng", desc: "Dễ đọc hơn", icon: "▦" },
                  ].map((d) => {
                    const isActive = density === d.id;
                    return (
                      <button
                        key={d.id}
                        onClick={() => setDensity(d.id as any)}
                        className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200 hover:scale-105
                          ${isActive ? "border-violet-400 bg-violet-50 shadow-md" : "border-gray-100 hover:border-gray-200"}`}
                      >
                        <span className="text-2xl">{d.icon}</span>
                        <span className={`text-sm font-semibold ${isActive ? "text-violet-700" : "text-gray-600"}`}>{d.label}</span>
                        <span className="text-xs text-gray-400">{d.desc}</span>
                        {isActive && <Check size={14} className="text-violet-500" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
                <h3 className="text-gray-800 text-sm mb-1">Định dạng số & Ngày tháng</h3>
                <p className="text-gray-400 text-xs mb-4">Cấu hình cách hiển thị số liệu và thời gian</p>
                <div className="space-y-3">
                  {[
                    { label: "Đơn vị tiền tệ", value: "VND (₫)", options: ["VND (₫)", "USD ($)", "EUR (€)"] },
                    { label: "Định dạng ngày", value: "DD/MM/YYYY", options: ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"] },
                    { label: "Múi giờ", value: "GMT+7 (Hà Nội)", options: ["GMT+7 (Hà Nội)", "GMT+0 (London)", "GMT-5 (New York)"] },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between py-3 border-b border-gray-50 last:border-0">
                      <span className="text-sm text-gray-600">{item.label}</span>
                      <select className="bg-[#f8faff] border border-gray-200 rounded-lg px-3 py-1.5 text-xs text-gray-700 outline-none focus:border-violet-400">
                        {item.options.map((o) => <option key={o}>{o}</option>)}
                      </select>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* ─── ACCOUNT ─── */}
          {activeSection === "account" && (
            <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-7 h-7 rounded-lg bg-violet-100 flex items-center justify-center">
                  <User size={14} className="text-violet-600" />
                </div>
                <div>
                  <h3 className="text-gray-800 text-sm">Thông tin tài khoản</h3>
                  <p className="text-gray-400 text-xs">Cập nhật thông tin cá nhân và liên lạc</p>
                </div>
              </div>
              <div className="flex items-center gap-4 mb-6 p-4 bg-gradient-to-r from-violet-50 to-indigo-50 rounded-xl">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-400 to-indigo-500 flex items-center justify-center text-white text-xl font-bold shadow-lg">
                  {user?.username?.[0]?.toUpperCase() ?? "U"}
                </div>
                <div>
                  <div className="font-semibold text-gray-800">{user?.username}</div>
                  <div className="text-sm text-gray-500">{user?.email ?? "—"}</div>
                  <span className="inline-block text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full mt-1 font-medium">{user?.roles?.[0] ?? "User"}</span>
                </div>
              </div>
              <div className="space-y-3">
                {[
                  { label: "Họ và tên", value: "Nguyễn Văn Admin" },
                  { label: "Email", value: "admin@lotusspa.vn" },
                  { label: "Số điện thoại", value: "0901234567" },
                  { label: "Chức vụ", value: "Giám đốc vận hành" },
                ].map((f) => (
                  <div key={f.label}>
                    <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">{f.label}</label>
                    <input
                      defaultValue={f.value}
                      className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 bg-gray-50 transition-all"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ─── SECURITY ─── */}
          {activeSection === "security" && (
            <div className="space-y-4">
              <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
                <div className="flex items-center gap-2 mb-5">
                  <div className="w-7 h-7 rounded-lg bg-red-100 flex items-center justify-center">
                    <Lock size={14} className="text-red-600" />
                  </div>
                  <div>
                    <h3 className="text-gray-800 text-sm">Đổi mật khẩu</h3>
                    <p className="text-gray-400 text-xs">Cập nhật mật khẩu đăng nhập</p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Mật khẩu hiện tại</label>
                    <input type="password" value={pwOld} onChange={e => setPwOld(e.target.value)} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 bg-gray-50" placeholder="••••••••" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Mật khẩu mới</label>
                    <input type="password" value={pwNew} onChange={e => setPwNew(e.target.value)} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 bg-gray-50" placeholder="••••••••" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Xác nhận mật khẩu mới</label>
                    <input type="password" value={pwConfirm} onChange={e => setPwConfirm(e.target.value)} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 bg-gray-50" placeholder="••••••••" />
                  </div>
                </div>
                {pwMsg && (
                  <div className={`mt-3 px-3 py-2 rounded-lg text-sm ${pwMsg.type === "ok" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"}`}>
                    {pwMsg.text}
                  </div>
                )}
                <button
                  onClick={handleChangePassword}
                  disabled={pwLoading}
                  className="mt-4 px-4 py-2.5 bg-red-500 text-white rounded-xl text-sm font-semibold hover:bg-red-600 transition-colors disabled:opacity-50"
                >
                  {pwLoading ? "Đang cập nhật..." : "Cập nhật mật khẩu"}
                </button>
              </div>
              <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
                <h3 className="text-gray-800 text-sm mb-1">Xác thực 2 bước (2FA)</h3>
                <p className="text-gray-400 text-xs mb-4">Tăng cường bảo mật cho tài khoản</p>
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                  <div>
                    <div className="text-sm font-semibold text-gray-700">Xác thực qua Authenticator App</div>
                    <div className="text-xs text-gray-400">Google Authenticator, Authy...</div>
                  </div>
                  <Toggle checked={false} onChange={() => {}} />
                </div>
              </div>
            </div>
          )}

          {/* ─── DATA ─── */}
          {activeSection === "data" && (
            <div className="space-y-4">
              <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
                <div className="flex items-center gap-2 mb-5">
                  <div className="w-7 h-7 rounded-lg bg-green-100 flex items-center justify-center">
                    <Database size={14} className="text-green-600" />
                  </div>
                  <div>
                    <h3 className="text-gray-800 text-sm">Backup & Khôi phục</h3>
                    <p className="text-gray-400 text-xs">Sao lưu dữ liệu hệ thống</p>
                  </div>
                </div>
                <div className="space-y-3">
                  {[
                    { label: "Lịch backup tự động", value: "Hàng ngày lúc 00:00", status: "✅ Đang hoạt động" },
                    { label: "Vị trí lưu trữ", value: "Cloud Storage (Google Drive)", status: "" },
                    { label: "Backup gần nhất", value: "25/03/2026 00:01", status: "✅ Thành công" },
                    { label: "Dung lượng đã dùng", value: "2.4 GB / 10 GB", status: "24%" },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between py-3 border-b border-gray-50 last:border-0">
                      <span className="text-sm text-gray-500">{item.label}</span>
                      <div className="text-right">
                        <div className="text-sm font-semibold text-gray-700">{item.value}</div>
                        {item.status && <div className="text-xs text-green-600">{item.status}</div>}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex gap-3 mt-4">
                  <button className="px-4 py-2.5 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl text-sm font-semibold hover:opacity-90 shadow-sm">Backup ngay</button>
                  <button className="px-4 py-2.5 border border-gray-200 text-gray-600 rounded-xl text-sm font-semibold hover:bg-gray-50">Xem lịch sử</button>
                </div>
              </div>

              <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 p-5">
                <h3 className="text-gray-800 text-sm mb-1">Xuất dữ liệu</h3>
                <p className="text-gray-400 text-xs mb-4">Tải xuống toàn bộ dữ liệu hệ thống</p>
                <div className="grid grid-cols-2 gap-3">
                  {["Khách hàng (CSV)", "Lịch hẹn (Excel)", "Doanh thu (PDF)", "Toàn bộ (ZIP)"].map((item) => (
                    <button key={item} className="flex items-center gap-2 px-3 py-2.5 border border-dashed border-gray-200 rounded-xl hover:border-violet-300 hover:bg-violet-50 text-sm text-gray-600 hover:text-violet-700 transition-all group">
                      <FileBarChart size={14} className="group-hover:text-violet-500" /> {item}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
