import { useState } from "react";
import {
  UserPlus, Search, Filter, Edit2, Trash2, Lock, Unlock,
  Shield, ShieldCheck, ShieldAlert, Eye, EyeOff, XCircle,
  Check, ChevronLeft, ChevronRight, Key, MoreVertical,
  UserX, RefreshCw, Copy, Mail, Phone, Calendar,
} from "lucide-react";

type Role = "super_admin" | "admin" | "manager" | "receptionist" | "therapist" | "accountant";
type Status = "active" | "inactive" | "locked";

interface Account {
  id: string;
  name: string;
  username: string;
  email: string;
  phone: string;
  role: Role;
  status: Status;
  branch: string;
  lastLogin: string;
  createdAt: string;
  avatar: string;
  twoFA: boolean;
  loginCount: number;
}

const roleConfig: Record<Role, { label: string; color: string; bg: string; border: string; icon: any; level: number }> = {
  super_admin:  { label: "Super Admin",   color: "text-red-700 dark:text-red-100",       bg: "bg-red-50 dark:bg-red-400/25",       border: "border-red-200 dark:border-red-300/60",       icon: ShieldAlert, level: 1 },
  admin:        { label: "Admin",         color: "text-violet-700 dark:text-violet-100", bg: "bg-violet-50 dark:bg-violet-400/25", border: "border-violet-200 dark:border-violet-300/60", icon: ShieldCheck, level: 2 },
  manager:      { label: "Quản lý",       color: "text-blue-700 dark:text-blue-100",      bg: "bg-blue-50 dark:bg-blue-400/25",      border: "border-blue-200 dark:border-blue-300/60",      icon: Shield,      level: 3 },
  receptionist: { label: "Lễ tân",        color: "text-emerald-700 dark:text-emerald-100",bg: "bg-emerald-50 dark:bg-emerald-400/25", border: "border-emerald-200 dark:border-emerald-300/60",icon: Shield,      level: 4 },
  therapist:    { label: "Kỹ thuật viên", color: "text-amber-700 dark:text-amber-100",    bg: "bg-amber-50 dark:bg-amber-400/25",    border: "border-amber-200 dark:border-amber-300/60",    icon: Shield,      level: 5 },
  accountant:   { label: "Kế toán",       color: "text-cyan-700 dark:text-cyan-100",      bg: "bg-cyan-50 dark:bg-cyan-400/25",      border: "border-cyan-200 dark:border-cyan-300/60",      icon: Shield,      level: 6 },
};

const statusConfig: Record<Status, { label: string; color: string; bg: string; dot: string }> = {
  active:   { label: "Hoạt động", color: "text-emerald-700", bg: "bg-emerald-50 border border-emerald-200", dot: "bg-emerald-500" },
  inactive: { label: "Không HĐ",  color: "text-gray-500",    bg: "bg-gray-50 border border-gray-200",       dot: "bg-gray-400" },
  locked:   { label: "Bị khóa",   color: "text-red-600",     bg: "bg-red-50 border border-red-200",         dot: "bg-red-500" },
};

const avatarGradients = [
  "from-violet-500 to-indigo-500", "from-pink-500 to-rose-500",
  "from-blue-500 to-cyan-500",     "from-amber-500 to-orange-500",
  "from-emerald-500 to-teal-500",  "from-red-500 to-pink-500",
  "from-indigo-500 to-purple-500", "from-cyan-500 to-blue-500",
];

const mockAccounts: Account[] = [
  { id: "ACC001", name: "Nguyễn Văn Admin", username: "admin", email: "admin@lotusspa.vn", phone: "0901234567", role: "super_admin", status: "active", branch: "Tất cả", lastLogin: "27/03/2026 09:15", createdAt: "01/01/2024", avatar: "NA", twoFA: true, loginCount: 1842 },
  { id: "ACC002", name: "Trần Thị Hoa", username: "hoatran", email: "hoa.tran@lotusspa.vn", phone: "0912345678", role: "admin", status: "active", branch: "Quận 1", lastLogin: "27/03/2026 08:42", createdAt: "15/03/2024", avatar: "TH", twoFA: true, loginCount: 924 },
  { id: "ACC003", name: "Lê Minh Tuấn", username: "tuanle", email: "tuan.le@lotusspa.vn", phone: "0923456789", role: "manager", status: "active", branch: "Quận 3", lastLogin: "26/03/2026 17:30", createdAt: "20/05/2024", avatar: "LT", twoFA: false, loginCount: 512 },
  { id: "ACC004", name: "Phạm Thu Hằng", username: "hangpham", email: "hang.pham@lotusspa.vn", phone: "0934567890", role: "receptionist", status: "active", branch: "Quận 7", lastLogin: "27/03/2026 09:00", createdAt: "10/06/2024", avatar: "PH", twoFA: false, loginCount: 387 },
  { id: "ACC005", name: "Võ Thị Lan", username: "lanvo", email: "lan.vo@lotusspa.vn", phone: "0945678901", role: "therapist", status: "active", branch: "Quận 1", lastLogin: "27/03/2026 08:15", createdAt: "01/07/2024", avatar: "VL", twoFA: false, loginCount: 298 },
  { id: "ACC006", name: "Đặng Văn Hùng", username: "hungdang", email: "hung.dang@lotusspa.vn", phone: "0956789012", role: "accountant", status: "active", branch: "Quận 1", lastLogin: "25/03/2026 16:45", createdAt: "15/08/2024", avatar: "ĐH", twoFA: true, loginCount: 156 },
  { id: "ACC007", name: "Nguyễn Thị Bích", username: "bichnguyen", email: "bich.nguyen@lotusspa.vn", phone: "0967890123", role: "manager", status: "inactive", branch: "Bình Thạnh", lastLogin: "10/03/2026 11:20", createdAt: "01/09/2024", avatar: "NB", twoFA: false, loginCount: 89 },
  { id: "ACC008", name: "Trương Quốc Bảo", username: "baotruong", email: "bao.truong@lotusspa.vn", phone: "0978901234", role: "receptionist", status: "locked", branch: "Thủ Đức", lastLogin: "05/03/2026 09:30", createdAt: "15/10/2024", avatar: "TB", twoFA: false, loginCount: 42 },
  { id: "ACC009", name: "Hoàng Thị Mai", username: "maihoang", email: "mai.hoang@lotusspa.vn", phone: "0989012345", role: "therapist", status: "active", branch: "Quận 7", lastLogin: "27/03/2026 07:55", createdAt: "20/11/2024", avatar: "HM", twoFA: false, loginCount: 67 },
  { id: "ACC010", name: "Lý Văn Nam", username: "namly", email: "nam.ly@lotusspa.vn", phone: "0990123456", role: "receptionist", status: "active", branch: "Quận 3", lastLogin: "26/03/2026 20:10", createdAt: "01/12/2024", avatar: "LN", twoFA: false, loginCount: 134 },
];

const permissionsMatrix: Record<Role, Record<string, boolean>> = {
  super_admin:  { dashboard: true,  appointments: true,  customers: true,  services: true,  staff: true,  branches: true,  reports: true,  accounts: true,  inventory: true,  logs: true  },
  admin:        { dashboard: true,  appointments: true,  customers: true,  services: true,  staff: true,  branches: true,  reports: true,  accounts: true,  inventory: true,  logs: true  },
  manager:      { dashboard: true,  appointments: true,  customers: true,  services: true,  staff: true,  branches: false, reports: true,  accounts: false, inventory: true,  logs: false },
  receptionist: { dashboard: true,  appointments: true,  customers: true,  services: false, staff: false, branches: false, reports: false, accounts: false, inventory: false, logs: false },
  therapist:    { dashboard: true,  appointments: true,  customers: false, services: false, staff: false, branches: false, reports: false, accounts: false, inventory: false, logs: false },
  accountant:   { dashboard: true,  appointments: false, customers: false, services: false, staff: false, branches: false, reports: true,  accounts: false, inventory: true,  logs: false },
};

const permLabels: Record<string, string> = {
  dashboard: "Tổng quan", appointments: "Lịch hẹn", customers: "Khách hàng",
  services: "Dịch vụ", staff: "Nhân viên", branches: "Chi nhánh",
  reports: "Báo cáo", accounts: "Tài khoản", inventory: "Kho vật dụng", logs: "Nhật ký",
};

const branches = ["Tất cả chi nhánh", "Quận 1", "Quận 3", "Quận 7", "Thủ Đức", "Bình Thạnh"];
const roleFilters = ["Tất cả", ...Object.keys(roleConfig).map(k => roleConfig[k as Role].label)];
const statusFilters = ["Tất cả", "Hoạt động", "Không HĐ", "Bị khóa"];

function PermBadge({ ok }: { ok: boolean }) {
  return ok
    ? <span className="perm-badge-ok flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100"><Check size={11} className="text-emerald-600" /></span>
    : <span className="perm-badge-no flex items-center justify-center w-6 h-6 rounded-full bg-gray-100"><XCircle size={11} className="text-gray-400" /></span>;
}

type ModalMode = "add" | "edit" | "view" | "delete" | "reset" | "perms" | null;

export function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>(mockAccounts);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("Tất cả");
  const [statusFilter, setStatusFilter] = useState("Tất cả");
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selected, setSelected] = useState<Account | null>(null);
  const [showPass, setShowPass] = useState(false);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"list" | "perms">("list");

  const filtered = accounts.filter((a) => {
    const q = search.toLowerCase();
    const matchQ = a.name.toLowerCase().includes(q) || a.username.toLowerCase().includes(q) || a.email.toLowerCase().includes(q);
    const matchRole = roleFilter === "Tất cả" || roleConfig[a.role].label === roleFilter;
    const matchStatus = statusFilter === "Tất cả" || statusConfig[a.status].label === statusFilter;
    return matchQ && matchRole && matchStatus;
  });

  const openModal = (mode: ModalMode, account?: Account) => {
    setSelected(account || null);
    setModalMode(mode);
    setOpenMenu(null);
  };

  const handleDelete = () => {
    if (selected) setAccounts(accounts.filter(a => a.id !== selected.id));
    setModalMode(null);
  };

  const toggleLock = (acc: Account) => {
    setAccounts(accounts.map(a =>
      a.id === acc.id ? { ...a, status: a.status === "locked" ? "active" : "locked" } : a
    ));
    setOpenMenu(null);
  };

  const counts = {
    total: accounts.length,
    active: accounts.filter(a => a.status === "active").length,
    locked: accounts.filter(a => a.status === "locked").length,
    admins: accounts.filter(a => a.role === "admin" || a.role === "super_admin").length,
  };

  return (
    <div className="space-y-5" onClick={() => setOpenMenu(null)}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-gray-500 text-sm">Quản lý tài khoản & phân quyền người dùng hệ thống</p>
        <button
          onClick={() => openModal("add")}
          className="flex items-center gap-2 bg-gradient-to-r from-violet-500 to-indigo-500 text-white px-4 py-2.5 rounded-xl hover:opacity-90 text-sm font-semibold shadow-md shadow-violet-200 transition-all hover:scale-105"
        >
          <UserPlus size={16} /> Thêm tài khoản
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Tổng tài khoản", value: counts.total, color: "text-violet-600", bg: "bg-violet-50", border: "border-violet-100", icon: "👥" },
          { label: "Đang hoạt động", value: counts.active, color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100", icon: "✅" },
          { label: "Bị khóa", value: counts.locked, color: "text-red-600", bg: "bg-red-50", border: "border-red-100", icon: "🔒" },
          { label: "Quản trị viên", value: counts.admins, color: "text-blue-600", bg: "bg-blue-50", border: "border-blue-100", icon: "🛡️" },
        ].map(item => (
          <div key={item.label} className={`${item.bg} border ${item.border} rounded-2xl p-4 flex items-center gap-3`}>
            <span className="text-2xl">{item.icon}</span>
            <div>
              <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
              <div className="text-xs text-gray-500 font-medium">{item.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Tab */}
      <div className="flex gap-1 bg-white/60 backdrop-blur border border-white/60 rounded-xl p-1 w-fit shadow-sm">
        {[{ id: "list", label: "Danh sách tài khoản" }, { id: "perms", label: "Ma trận phân quyền" }].map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as any)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === t.id ? "bg-gradient-to-r from-violet-500 to-indigo-500 text-white shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "list" && (
        <>
          {/* Filters */}
          <div className="bg-white/80 backdrop-blur rounded-2xl p-4 shadow-sm border border-white/60 space-y-3">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 flex-1">
                <Search size={15} className="text-gray-400 flex-shrink-0" />
                <input type="text" placeholder="Tìm tên, username, email..." value={search} onChange={e => setSearch(e.target.value)}
                  className="bg-transparent text-sm text-gray-700 placeholder-gray-400 outline-none w-full" />
              </div>
              <div className="flex gap-2">
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                  className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5 text-sm text-gray-700 outline-none cursor-pointer">
                  {statusFilters.map(s => <option key={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              {roleFilters.map(f => (
                <button key={f} onClick={() => setRoleFilter(f)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${roleFilter === f ? "bg-gradient-to-r from-violet-500 to-indigo-500 text-white shadow-sm" : "bg-gray-100 text-gray-500 hover:bg-violet-50 hover:text-violet-600"}`}>
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Table */}
          <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/80">
                    {["Tài khoản", "Username", "Vai trò", "Chi nhánh", "Trạng thái", "Đăng nhập cuối", "2FA", ""].map((h, i) => (
                      <th key={i} className={`text-left px-4 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider ${i === 1 ? "hidden md:table-cell" : i === 3 ? "hidden lg:table-cell" : i === 5 ? "hidden xl:table-cell" : i === 6 ? "hidden sm:table-cell" : ""}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filtered.map((acc, idx) => {
                    const role = roleConfig[acc.role];
                    const st = statusConfig[acc.status];
                    const RIcon = role.icon;
                    return (
                      <tr key={acc.id} className="hover:bg-violet-50/30 transition-colors group">
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-3">
                            <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${avatarGradients[idx % avatarGradients.length]} flex items-center justify-center text-white text-xs font-bold flex-shrink-0 shadow-sm`}>
                              {acc.avatar}
                            </div>
                            <div>
                              <div className="text-sm font-semibold text-gray-800">{acc.name}</div>
                              <div className="text-xs text-gray-400 flex items-center gap-1"><Mail size={9} />{acc.email}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 hidden md:table-cell">
                          <span className="font-mono text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-lg">{acc.username}</span>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg border ${role.bg} ${role.color} ${role.border}`}>
                            <RIcon size={11} />{role.label}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 hidden lg:table-cell">
                          <span className="text-xs text-gray-600">{acc.branch}</span>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg ${st.bg} ${st.color}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />{st.label}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 hidden xl:table-cell">
                          <div className="text-xs text-gray-500">{acc.lastLogin}</div>
                          <div className="text-xs text-gray-400">{acc.loginCount} lần đăng nhập</div>
                        </td>
                        <td className="px-4 py-3.5 hidden sm:table-cell">
                          {acc.twoFA
                            ? <span className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-400/30 dark:text-emerald-100 dark:border dark:border-emerald-300/50 px-2 py-1 rounded-lg font-semibold">✓ Bật</span>
                            : <span className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded-lg">Tắt</span>}
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="relative flex items-center gap-1" onClick={e => e.stopPropagation()}>
                            <button onClick={() => openModal("edit", acc)} className="p-1.5 rounded-lg hover:bg-violet-100 text-gray-400 hover:text-violet-600 transition-colors" title="Chỉnh sửa">
                              <Edit2 size={13} />
                            </button>
                            <button
                              onClick={() => setOpenMenu(openMenu === acc.id ? null : acc.id)}
                              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                            >
                              <MoreVertical size={13} />
                            </button>
                            {openMenu === acc.id && (
                              <div className="absolute right-0 top-full mt-1 w-44 bg-white rounded-xl shadow-xl border border-gray-100 z-50 py-1 overflow-hidden">
                                <button onClick={() => openModal("view", acc)} className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-gray-700 hover:bg-violet-50 hover:text-violet-700 transition-colors">
                                  <Eye size={14} /> Xem chi tiết
                                </button>
                                <button onClick={() => openModal("reset", acc)} className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-gray-700 hover:bg-amber-50 hover:text-amber-700 transition-colors">
                                  <Key size={14} /> Đặt lại mật khẩu
                                </button>
                                <button onClick={() => toggleLock(acc)} className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm transition-colors ${acc.status === "locked" ? "text-gray-700 hover:bg-emerald-50 hover:text-emerald-700" : "text-gray-700 hover:bg-orange-50 hover:text-orange-700"}`}>
                                  {acc.status === "locked" ? <><Unlock size={14} /> Mở khóa</> : <><Lock size={14} /> Khóa tài khoản</>}
                                </button>
                                <div className="border-t border-gray-100 my-1" />
                                <button onClick={() => openModal("delete", acc)} className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors">
                                  <Trash2 size={14} /> Xóa tài khoản
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between px-4 py-3.5 border-t border-gray-100 bg-gray-50/50">
              <span className="text-xs text-gray-400">Hiển thị <span className="font-semibold text-gray-600">{filtered.length}</span> / {accounts.length} tài khoản</span>
              <div className="flex items-center gap-1">
                <button className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400 hover:bg-violet-50 hover:text-violet-600 transition-colors"><ChevronLeft size={14} /></button>
                <button className="w-8 h-8 rounded-lg bg-gradient-to-r from-violet-500 to-indigo-500 text-white text-xs font-semibold shadow-sm">1</button>
                <button className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400 hover:bg-violet-50 hover:text-violet-600 transition-colors"><ChevronRight size={14} /></button>
              </div>
            </div>
          </div>
        </>
      )}

      {activeTab === "perms" && (
        <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <h3 className="text-gray-800 dark:text-gray-100 text-sm font-semibold">Ma trận phân quyền hệ thống</h3>
            <p className="text-gray-400 dark:text-gray-300 text-xs mt-0.5">Quyền truy cập theo vai trò</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/80">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-200 uppercase tracking-wider w-40">Chức năng</th>
                  {Object.entries(roleConfig).map(([k, v]) => (
                    <th key={k} className="px-3 py-3 text-center">
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-lg border ${v.bg} ${v.color} ${v.border}`}>
                        {v.label}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {Object.entries(permLabels).map(([perm, label]) => (
                  <tr key={perm} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-100">{label}</td>
                    {Object.keys(roleConfig).map(role => (
                      <td key={role} className="px-3 py-3 text-center">
                        <div className="flex justify-center">
                          <PermBadge ok={permissionsMatrix[role as Role][perm]} />
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── MODALS ─── */}

      {/* Add/Edit Modal */}
      {(modalMode === "add" || modalMode === "edit") && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 border border-gray-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-gray-900 font-semibold">{modalMode === "add" ? "Thêm tài khoản mới" : "Chỉnh sửa tài khoản"}</h3>
                <p className="text-gray-400 text-xs mt-0.5">{modalMode === "add" ? "Điền đầy đủ thông tin tài khoản" : `Đang chỉnh sửa: ${selected?.name}`}</p>
              </div>
              <button onClick={() => setModalMode(null)} className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center text-gray-400"><XCircle size={18} /></button>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Họ và tên *</label>
                  <input defaultValue={selected?.name} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 bg-gray-50" placeholder="Nguyễn Văn A" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Tên đăng nhập *</label>
                  <input defaultValue={selected?.username} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 bg-gray-50 font-mono" placeholder="username" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Số điện thoại</label>
                  <input defaultValue={selected?.phone} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 bg-gray-50" placeholder="09xxxxxxxx" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Email *</label>
                  <input defaultValue={selected?.email} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 bg-gray-50" placeholder="email@lotusspa.vn" />
                </div>
                {modalMode === "add" && (
                  <div className="col-span-2">
                    <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Mật khẩu *</label>
                    <div className="relative">
                      <input type={showPass ? "text" : "password"} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100 bg-gray-50 pr-10" placeholder="••••••••" />
                      <button onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                        {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    </div>
                  </div>
                )}
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Vai trò *</label>
                  <select defaultValue={selected?.role} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 bg-gray-50 cursor-pointer">
                    {Object.entries(roleConfig).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Chi nhánh *</label>
                  <select defaultValue={selected?.branch} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 bg-gray-50 cursor-pointer">
                    {branches.map(b => <option key={b}>{b}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Trạng thái</label>
                  <select defaultValue={selected?.status} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-violet-400 bg-gray-50 cursor-pointer">
                    <option value="active">Hoạt động</option>
                    <option value="inactive">Không hoạt động</option>
                    <option value="locked">Bị khóa</option>
                  </select>
                </div>
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl border border-gray-200">
                  <div>
                    <div className="text-xs font-semibold text-gray-600">Bật xác thực 2 bước</div>
                    <div className="text-xs text-gray-400">Tăng bảo mật tài khoản</div>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setModalMode(null)} className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 font-medium transition-colors">Hủy</button>
              <button onClick={() => setModalMode(null)} className="flex-1 px-4 py-2.5 bg-gradient-to-r from-violet-500 to-indigo-500 text-white rounded-xl text-sm font-semibold shadow-md shadow-violet-200 hover:opacity-90 transition-all">
                {modalMode === "add" ? "Tạo tài khoản" : "Lưu thay đổi"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Modal */}
      {modalMode === "view" && selected && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-100">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-gray-900 font-semibold">Chi tiết tài khoản</h3>
              <button onClick={() => setModalMode(null)} className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center text-gray-400"><XCircle size={18} /></button>
            </div>
            <div className="flex items-center gap-4 mb-5 p-4 bg-gradient-to-r from-violet-50 to-indigo-50 rounded-xl">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center text-white font-bold text-lg shadow-lg">
                {selected.avatar}
              </div>
              <div>
                <div className="font-bold text-gray-800">{selected.name}</div>
                <div className="text-sm text-gray-500">@{selected.username}</div>
                <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-lg mt-1 border ${roleConfig[selected.role].bg} ${roleConfig[selected.role].color} ${roleConfig[selected.role].border}`}>
                  {roleConfig[selected.role].label}
                </span>
              </div>
            </div>
            <div className="space-y-2.5">
              {[
                { icon: Mail, label: "Email", value: selected.email },
                { icon: Phone, label: "Điện thoại", value: selected.phone },
                { icon: MapPin2, label: "Chi nhánh", value: selected.branch },
                { icon: Calendar, label: "Ngày tạo", value: selected.createdAt },
                { icon: RefreshCw, label: "Đăng nhập cuối", value: selected.lastLogin },
              ].map(row => {
                const Icon = row.icon;
                return (
                  <div key={row.label} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                    <Icon size={14} className="text-violet-400 flex-shrink-0" />
                    <span className="text-xs text-gray-500 w-28">{row.label}</span>
                    <span className="text-sm font-medium text-gray-700">{row.value}</span>
                  </div>
                );
              })}
              <div className="flex items-center gap-3 py-2">
                <Key size={14} className="text-violet-400 flex-shrink-0" />
                <span className="text-xs text-gray-500 w-28">Xác thực 2FA</span>
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${selected.twoFA ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-500"}`}>
                  {selected.twoFA ? "✓ Đã bật" : "Chưa bật"}
                </span>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setModalMode(null)} className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 font-medium">Đóng</button>
              <button onClick={() => openModal("edit", selected)} className="flex-1 px-4 py-2.5 bg-gradient-to-r from-violet-500 to-indigo-500 text-white rounded-xl text-sm font-semibold hover:opacity-90">Chỉnh sửa</button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Password */}
      {modalMode === "reset" && selected && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 border border-gray-100">
            <div className="text-center mb-5">
              <div className="w-14 h-14 bg-amber-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                <Key size={24} className="text-amber-600" />
              </div>
              <h3 className="text-gray-900 font-semibold">Đặt lại mật khẩu</h3>
              <p className="text-gray-400 text-sm mt-1">Cho tài khoản <strong>{selected.name}</strong></p>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Mật khẩu mới</label>
                <div className="relative">
                  <input type={showPass ? "text" : "password"} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-amber-400 bg-gray-50 pr-20" placeholder="••••••••" />
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
                    <button onClick={() => setShowPass(!showPass)} className="p-1 text-gray-400 hover:text-gray-600"><Eye size={13} /></button>
                    <button className="p-1 text-gray-400 hover:text-gray-600" title="Tạo ngẫu nhiên"><RefreshCw size={13} /></button>
                    <button className="p-1 text-gray-400 hover:text-gray-600" title="Sao chép"><Copy size={13} /></button>
                  </div>
                </div>
              </div>
              <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
                <p className="text-xs text-amber-700">⚠️ Người dùng sẽ nhận mật khẩu mới qua email và phải đổi lại khi đăng nhập lần đầu.</p>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setModalMode(null)} className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 font-medium">Hủy</button>
              <button onClick={() => setModalMode(null)} className="flex-1 px-4 py-2.5 bg-amber-500 text-white rounded-xl text-sm font-semibold hover:bg-amber-600 shadow-md shadow-amber-200">Xác nhận</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {modalMode === "delete" && selected && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 border border-gray-100">
            <div className="text-center mb-5">
              <div className="w-14 h-14 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                <UserX size={24} className="text-red-500" />
              </div>
              <h3 className="text-gray-900 font-semibold">Xóa tài khoản?</h3>
              <p className="text-gray-500 text-sm mt-2">Bạn có chắc muốn xóa tài khoản <strong className="text-gray-800">{selected.name}</strong>? Hành động này không thể hoàn tác.</p>
            </div>
            <div className="p-3 bg-red-50 border border-red-100 rounded-xl mb-4">
              <p className="text-xs text-red-600">🚨 Tất cả dữ liệu liên quan (lịch sử hoạt động, phân công) sẽ bị xóa vĩnh viễn.</p>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setModalMode(null)} className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 font-medium">Hủy</button>
              <button onClick={handleDelete} className="flex-1 px-4 py-2.5 bg-red-500 text-white rounded-xl text-sm font-semibold hover:bg-red-600 shadow-md shadow-red-200">Xóa tài khoản</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// helper component only used inside this file
function MapPin2({ size, className }: { size: number; className?: string }) {
  return <MapPin size={size} className={className} />;
}
