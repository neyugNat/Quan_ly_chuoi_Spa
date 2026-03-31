import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../lib/api';
import {
  UserPlus, Search, Edit2, Trash2, Lock, Unlock,
  Shield, ShieldCheck, ShieldAlert, Eye, XCircle,
  Check, ChevronLeft, ChevronRight, MoreVertical,
  UserX,
} from 'lucide-react';

type Role = string;
type Status = 'active' | 'inactive' | 'locked';

type Account = {
  id: number;
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
};

const roleConfig: Record<string, { label: string; color: string; bg: string; border: string; icon: any }> = {
  super_admin: { label: 'Super Admin', color: 'text-red-700 dark:text-red-100', bg: 'bg-red-50 dark:bg-red-400/25', border: 'border-red-200 dark:border-red-300/60', icon: ShieldAlert },
  branch_manager: { label: 'Quản lý chi nhánh', color: 'text-blue-700 dark:text-blue-100', bg: 'bg-blue-50 dark:bg-blue-400/25', border: 'border-blue-200 dark:border-blue-300/60', icon: ShieldCheck },
  reception: { label: 'Lễ tân', color: 'text-emerald-700 dark:text-emerald-100', bg: 'bg-emerald-50 dark:bg-emerald-400/25', border: 'border-emerald-200 dark:border-emerald-300/60', icon: Shield },
  cashier: { label: 'Thu ngân', color: 'text-cyan-700 dark:text-cyan-100', bg: 'bg-cyan-50 dark:bg-cyan-400/25', border: 'border-cyan-200 dark:border-cyan-300/60', icon: Shield },
  technician: { label: 'Kỹ thuật viên', color: 'text-amber-700 dark:text-amber-100', bg: 'bg-amber-50 dark:bg-amber-400/25', border: 'border-amber-200 dark:border-amber-300/60', icon: Shield },
  warehouse: { label: 'Kho', color: 'text-violet-700 dark:text-violet-100', bg: 'bg-violet-50 dark:bg-violet-400/25', border: 'border-violet-200 dark:border-violet-300/60', icon: Shield },
};

const statusConfig: Record<Status, { label: string; color: string; bg: string; dot: string }> = {
  active: { label: 'Hoạt động', color: 'text-emerald-700', bg: 'bg-emerald-50 border border-emerald-200', dot: 'bg-emerald-500' },
  inactive: { label: 'Không HĐ', color: 'text-gray-500', bg: 'bg-gray-50 border border-gray-200', dot: 'bg-gray-400' },
  locked: { label: 'Bị khóa', color: 'text-red-600', bg: 'bg-red-50 border border-red-200', dot: 'bg-red-500' },
};

const avatarGradients = [
  'from-violet-500 to-indigo-500', 'from-pink-500 to-rose-500',
  'from-blue-500 to-cyan-500', 'from-amber-500 to-orange-500',
  'from-emerald-500 to-teal-500', 'from-red-500 to-pink-500',
  'from-indigo-500 to-purple-500', 'from-cyan-500 to-blue-500',
];

const permissionsMatrix: Record<string, Record<string, boolean>> = {
  super_admin: { dashboard: true, appointments: true, customers: true, services: true, staff: true, branches: true, reports: true, accounts: true, inventory: true, logs: true },
  branch_manager: { dashboard: true, appointments: true, customers: true, services: true, staff: true, branches: false, reports: true, accounts: false, inventory: true, logs: false },
  reception: { dashboard: true, appointments: true, customers: true, services: false, staff: false, branches: false, reports: false, accounts: false, inventory: false, logs: false },
  cashier: { dashboard: false, appointments: false, customers: true, services: false, staff: false, branches: false, reports: false, accounts: false, inventory: false, logs: false },
  technician: { dashboard: false, appointments: true, customers: false, services: false, staff: false, branches: false, reports: false, accounts: false, inventory: false, logs: false },
  warehouse: { dashboard: false, appointments: false, customers: false, services: false, staff: false, branches: false, reports: false, accounts: false, inventory: true, logs: false },
};

const permLabels: Record<string, string> = {
  dashboard: 'Tổng quan', appointments: 'Lịch hẹn', customers: 'Khách hàng',
  services: 'Dịch vụ', staff: 'Nhân viên', branches: 'Chi nhánh',
  reports: 'Báo cáo', accounts: 'Tài khoản', inventory: 'Kho vật dụng', logs: 'Nhật ký',
};

function PermBadge({ ok }: { ok: boolean }) {
  return ok
    ? <span className="perm-badge-ok flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100"><Check size={11} className="text-emerald-600" /></span>
    : <span className="perm-badge-no flex items-center justify-center w-6 h-6 rounded-full bg-gray-100"><XCircle size={11} className="text-gray-400" /></span>;
}

function initialsOf(username: string) {
  if (!username) return 'U';
  return username.slice(0, 2).toUpperCase();
}

export function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('Tất cả');
  const [statusFilter, setStatusFilter] = useState('Tất cả');
  const [selected, setSelected] = useState<Account | null>(null);
  const [openMenu, setOpenMenu] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'list' | 'perms'>('list');

  async function load() {
    try {
      const data = await apiFetch('/api/users');
      const rows = data?.items || [];

      const mapped: Account[] = rows.map((row: any) => {
        const role = String((row?.roles || [])[0] || 'reception');
        const isActive = Boolean(row?.is_active);
        const status: Status = isActive ? 'active' : 'inactive';

        return {
          id: Number(row?.id || 0),
          name: row?.username || `user_${row?.id}`,
          username: row?.username || '-',
          email: '-',
          phone: '-',
          role,
          status,
          branch: (row?.branch_ids || []).join(', ') || '-',
          lastLogin: '-',
          createdAt: String(row?.created_at || '').slice(0, 10) || '-',
          avatar: initialsOf(row?.username || ''),
          twoFA: false,
          loginCount: 0,
        };
      });
      setAccounts(mapped);
    } catch {
      setAccounts([]);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function toggleActive(acc: Account) {
    try {
      await apiFetch(`/api/users/${acc.id}`, {
        method: 'PUT',
        body: JSON.stringify({ is_active: acc.status !== 'active' }),
      });
      await load();
    } catch {}
    setOpenMenu(null);
  }

  async function deleteAccount(acc: Account) {
    try {
      await apiFetch(`/api/users/${acc.id}`, { method: 'DELETE' });
      await load();
    } catch {}
    setSelected(null);
    setOpenMenu(null);
  }

  const roleFilters = ['Tất cả', ...Array.from(new Set(accounts.map((a) => roleConfig[a.role]?.label || a.role)))] ;
  const statusFilters = ['Tất cả', 'Hoạt động', 'Không HĐ', 'Bị khóa'];

  const filtered = accounts.filter((a) => {
    const q = search.toLowerCase();
    const matchQ = a.name.toLowerCase().includes(q) || a.username.toLowerCase().includes(q);
    const roleLabel = roleConfig[a.role]?.label || a.role;
    const matchRole = roleFilter === 'Tất cả' || roleLabel === roleFilter;
    const matchStatus = statusFilter === 'Tất cả' || statusConfig[a.status].label === statusFilter;
    return matchQ && matchRole && matchStatus;
  });

  const counts = {
    total: accounts.length,
    active: accounts.filter(a => a.status === 'active').length,
    locked: accounts.filter(a => a.status === 'locked').length,
    admins: accounts.filter(a => a.role === 'super_admin' || a.role === 'branch_manager').length,
  };

  const permRoles = useMemo(() => {
    const roles = Array.from(new Set(accounts.map((a) => a.role)));
    return roles.length ? roles : Object.keys(permissionsMatrix);
  }, [accounts]);

  return (
    <div className="space-y-5" onClick={() => setOpenMenu(null)}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-gray-500 text-sm">Quản lý tài khoản & phân quyền người dùng hệ thống</p>
        <button
          className="flex items-center gap-2 bg-gradient-to-r from-violet-500 to-indigo-500 text-white px-4 py-2.5 rounded-xl hover:opacity-90 text-sm font-semibold shadow-md shadow-violet-200 transition-all hover:scale-105"
        >
          <UserPlus size={16} /> Thêm tài khoản
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Tổng tài khoản', value: counts.total, color: 'text-violet-600', bg: 'bg-violet-50', border: 'border-violet-100', icon: '👥' },
          { label: 'Đang hoạt động', value: counts.active, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100', icon: '✅' },
          { label: 'Bị khóa', value: counts.locked, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-100', icon: '🔒' },
          { label: 'Quản trị viên', value: counts.admins, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-100', icon: '🛡️' },
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

      <div className="flex gap-1 bg-white/60 backdrop-blur border border-white/60 rounded-xl p-1 w-fit shadow-sm">
        {[{ id: 'list', label: 'Danh sách tài khoản' }, { id: 'perms', label: 'Ma trận phân quyền' }].map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as any)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === t.id ? 'bg-gradient-to-r from-violet-500 to-indigo-500 text-white shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'list' && (
        <>
          <div className="bg-white/80 backdrop-blur rounded-2xl p-4 shadow-sm border border-white/60 space-y-3">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 flex-1">
                <Search size={15} className="text-gray-400 flex-shrink-0" />
                <input type="text" placeholder="Tìm tên, username..." value={search} onChange={e => setSearch(e.target.value)}
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
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${roleFilter === f ? 'bg-gradient-to-r from-violet-500 to-indigo-500 text-white shadow-sm' : 'bg-gray-100 text-gray-500 hover:bg-violet-50 hover:text-violet-600'}`}>
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/80">
                    {['Tài khoản', 'Username', 'Vai trò', 'Chi nhánh', 'Trạng thái', 'Ngày tạo', '2FA', ''].map((h, i) => (
                      <th key={i} className={`text-left px-4 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider ${i === 1 ? 'hidden md:table-cell' : i === 3 ? 'hidden lg:table-cell' : i === 5 ? 'hidden xl:table-cell' : i === 6 ? 'hidden sm:table-cell' : ''}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filtered.map((acc, idx) => {
                    const role = roleConfig[acc.role] || { label: acc.role, color: 'text-gray-700', bg: 'bg-gray-50', border: 'border-gray-200', icon: Shield };
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
                              <div className="text-xs text-gray-400">ID: {acc.id}</div>
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
                          <div className="text-xs text-gray-500">{acc.createdAt}</div>
                        </td>
                        <td className="px-4 py-3.5 hidden sm:table-cell">
                          {acc.twoFA
                            ? <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded-lg font-semibold">✓ Bật</span>
                            : <span className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded-lg">Tắt</span>}
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="relative flex items-center gap-1" onClick={e => e.stopPropagation()}>
                            <button onClick={() => setSelected(acc)} className="p-1.5 rounded-lg hover:bg-violet-100 text-gray-400 hover:text-violet-600 transition-colors" title="Xem">
                              <Eye size={13} />
                            </button>
                            <button
                              onClick={() => setOpenMenu(openMenu === acc.id ? null : acc.id)}
                              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                            >
                              <MoreVertical size={13} />
                            </button>
                            {openMenu === acc.id && (
                              <div className="absolute right-0 top-full mt-1 w-44 bg-white rounded-xl shadow-xl border border-gray-100 z-50 py-1 overflow-hidden">
                                <button onClick={() => toggleActive(acc)} className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-gray-700 hover:bg-amber-50 hover:text-amber-700 transition-colors">
                                  {acc.status === 'active' ? <><Lock size={14} /> Vô hiệu hóa</> : <><Unlock size={14} /> Kích hoạt</>}
                                </button>
                                <button onClick={() => setSelected(acc)} className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-gray-700 hover:bg-violet-50 hover:text-violet-700 transition-colors">
                                  <Edit2 size={14} /> Xem chi tiết
                                </button>
                                <div className="border-t border-gray-100 my-1" />
                                <button onClick={() => deleteAccount(acc)} className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors">
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

      {activeTab === 'perms' && (
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
                  {permRoles.map((roleName) => {
                    const cfg = roleConfig[roleName] || { label: roleName, color: 'text-gray-700', bg: 'bg-gray-50', border: 'border-gray-200' };
                    return (
                      <th key={roleName} className="px-3 py-3 text-center">
                        <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-lg border ${cfg.bg} ${cfg.color} ${cfg.border}`}>
                          {cfg.label}
                        </span>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {Object.entries(permLabels).map(([perm, label]) => (
                  <tr key={perm} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-100">{label}</td>
                    {permRoles.map((roleName) => (
                      <td key={roleName} className="px-3 py-3 text-center">
                        <div className="flex justify-center">
                          <PermBadge ok={Boolean(permissionsMatrix[roleName]?.[perm])} />
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

      {selected && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-100" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-gray-900 font-semibold">Chi tiết tài khoản</h3>
              <button onClick={() => setSelected(null)} className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center text-gray-400"><XCircle size={18} /></button>
            </div>
            <div className="flex items-center gap-4 mb-5 p-4 bg-gradient-to-r from-violet-50 to-indigo-50 rounded-xl">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center text-white font-bold text-lg shadow-lg">
                {selected.avatar}
              </div>
              <div>
                <div className="font-bold text-gray-800">{selected.name}</div>
                <div className="text-sm text-gray-500">@{selected.username}</div>
                <span className="text-xs text-gray-500">Vai trò: {roleConfig[selected.role]?.label || selected.role}</span>
              </div>
            </div>
            <div className="space-y-2 text-sm text-gray-600">
              <div>ID: {selected.id}</div>
              <div>Chi nhánh: {selected.branch}</div>
              <div>Ngày tạo: {selected.createdAt}</div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setSelected(null)} className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 font-medium">Đóng</button>
              <button onClick={() => deleteAccount(selected)} className="flex-1 px-4 py-2.5 bg-red-500 text-white rounded-xl text-sm font-semibold hover:bg-red-600">Xóa</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
