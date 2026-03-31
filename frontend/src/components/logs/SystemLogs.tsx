import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../lib/api';
import {
  Search, Download, RefreshCw,
  LogIn, LogOut, Edit, Trash2, Plus, Eye,
  AlertTriangle, Info, CheckCircle, XCircle,
  Clock, User, Monitor, Globe, ChevronLeft, ChevronRight,
  Activity, Database, Key, Lock,
} from 'lucide-react';

type LogAction =
  | 'login' | 'logout' | 'login_failed'
  | 'create' | 'update' | 'delete' | 'view'
  | 'export' | 'import' | 'reset_password' | 'lock_account' | 'permission_change';

type LogSeverity = 'info' | 'warning' | 'error' | 'success';

type LogEntry = {
  id: string;
  timestamp: string;
  date: string;
  account: string;
  accountId: string;
  role: string;
  action: LogAction;
  resource: string;
  resourceId: string;
  detail: string;
  ip: string;
  device: string;
  browser: string;
  severity: LogSeverity;
  status: 'success' | 'failed';
};

const actionConfig: Record<LogAction, { label: string; icon: any; color: string; bg: string; border: string }> = {
  login: { label: 'Đăng nhập', icon: LogIn, color: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  logout: { label: 'Đăng xuất', icon: LogOut, color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200' },
  login_failed: { label: 'Đăng nhập thất bại', icon: Lock, color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200' },
  create: { label: 'Tạo mới', icon: Plus, color: 'text-blue-700 dark:text-blue-100', bg: 'bg-blue-50 dark:bg-blue-400/25', border: 'border-blue-200 dark:border-blue-300/60' },
  update: { label: 'Cập nhật', icon: Edit, color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200' },
  delete: { label: 'Xóa', icon: Trash2, color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200' },
  view: { label: 'Xem', icon: Eye, color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200' },
  export: { label: 'Xuất dữ liệu', icon: Download, color: 'text-violet-700', bg: 'bg-violet-50', border: 'border-violet-200' },
  import: { label: 'Nhập dữ liệu', icon: Database, color: 'text-cyan-700', bg: 'bg-cyan-50', border: 'border-cyan-200' },
  reset_password: { label: 'Đặt lại mật khẩu', icon: Key, color: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-200' },
  lock_account: { label: 'Khóa tài khoản', icon: Lock, color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200' },
  permission_change: { label: 'Thay đổi quyền', icon: Activity, color: 'text-purple-700 dark:text-purple-50', bg: 'bg-purple-50 dark:bg-purple-300/35', border: 'border-purple-200 dark:border-purple-200/75' },
};

const severityConfig: Record<LogSeverity, { icon: any; color: string; bg: string }> = {
  info: { icon: Info, color: 'text-blue-600 dark:text-blue-100', bg: 'bg-blue-50 dark:bg-blue-300/30' },
  warning: { icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50' },
  error: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50' },
  success: { icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50' },
};

const severityLabels: Record<LogSeverity, string> = { info: 'Thông tin', warning: 'Cảnh báo', error: 'Lỗi', success: 'Thành công' };

function normalizeAction(rawAction: string): LogAction {
  const action = String(rawAction || '').toLowerCase();
  if (action.includes('login') && action.includes('failed')) return 'login_failed';
  if (action.includes('login')) return 'login';
  if (action.includes('logout')) return 'logout';
  if (action.includes('create')) return 'create';
  if (action.includes('delete')) return 'delete';
  if (action.includes('view') || action.includes('list') || action.includes('get')) return 'view';
  if (action.includes('export')) return 'export';
  if (action.includes('import')) return 'import';
  if (action.includes('reset') || action.includes('set_password')) return 'reset_password';
  if (action.includes('lock')) return 'lock_account';
  if (action.includes('permission') || action.includes('role')) return 'permission_change';
  return 'update';
}

function normalizeSeverity(action: LogAction): LogSeverity {
  if (action === 'login_failed') return 'error';
  if (action === 'delete' || action === 'lock_account' || action === 'permission_change') return 'warning';
  if (action === 'login' || action === 'create') return 'success';
  return 'info';
}

function formatDateTime(value: any) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '-';
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, '0');
  const mi = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  return `${dd}/${mm}/${yyyy} ${hh}:${mi}:${ss}`;
}

export function SystemLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('Tất cả');
  const [severityFilter, setSeverityFilter] = useState('Tất cả');
  const [dateFilter, setDateFilter] = useState('Tất cả');
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [page, setPage] = useState(1);
  const PER_PAGE = 10;

  async function load() {
    try {
      const [logRes, usersRes] = await Promise.all([
        apiFetch('/api/audit-logs?limit=500'),
        apiFetch('/api/users'),
      ]);

      const userById = new Map<number, string>();
      (usersRes?.items || []).forEach((u: any) => userById.set(Number(u?.id), u?.username || `user_${u?.id}`));

      const mapped: LogEntry[] = (logRes?.items || []).map((row: any) => {
        const action = normalizeAction(String(row?.action || ''));
        const severity = normalizeSeverity(action);
        const status = action === 'login_failed' ? 'failed' : 'success';
        const createdAt = String(row?.created_at || '');
        const dateOnly = createdAt.slice(0, 10);

        return {
          id: `LOG-${row?.id}`,
          timestamp: formatDateTime(createdAt),
          date: dateOnly,
          account: userById.get(Number(row?.user_id || 0)) || `user_${row?.user_id || 'unknown'}`,
          accountId: String(row?.user_id || '-'),
          role: '-',
          action,
          resource: row?.entity || 'Hệ thống',
          resourceId: String(row?.id || '-'),
          detail: `${row?.action || ''}${row?.entity ? ` • ${row.entity}` : ''}`,
          ip: '-',
          device: '-',
          browser: '-',
          severity,
          status,
        };
      });
      setLogs(mapped);
    } catch {
      setLogs([]);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const today = new Date();
    const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayKey = `${yesterday.getFullYear()}-${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`;

    return logs.filter(log => {
      const q = search.toLowerCase();
      const matchQ = log.account.toLowerCase().includes(q) || log.detail.toLowerCase().includes(q)
        || log.resource.toLowerCase().includes(q) || log.id.toLowerCase().includes(q) || log.ip.includes(q);
      const matchAction = actionFilter === 'Tất cả' || actionConfig[log.action].label === actionFilter;
      const matchSeverity = severityFilter === 'Tất cả' || severityLabels[log.severity] === severityFilter;
      const matchDate = dateFilter === 'Tất cả'
        || (dateFilter === 'Hôm nay' && log.date === todayKey)
        || (dateFilter === 'Hôm qua' && log.date === yesterdayKey);
      return matchQ && matchAction && matchSeverity && matchDate;
    });
  }, [logs, search, actionFilter, severityFilter, dateFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const paged = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  const counts = {
    total: logs.length,
    errors: logs.filter(l => l.severity === 'error' || l.status === 'failed').length,
    warnings: logs.filter(l => l.severity === 'warning').length,
    today: (() => {
      const now = new Date();
      const key = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      return logs.filter(l => l.date === key).length;
    })(),
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-gray-500 text-sm">Theo dõi toàn bộ hoạt động & sự kiện hệ thống</p>
        <div className="flex items-center gap-2">
          <button onClick={load} className="flex items-center gap-1.5 px-3.5 py-2.5 border border-gray-200 bg-white/80 backdrop-blur rounded-xl text-xs font-semibold text-gray-500 hover:bg-gray-50 transition-all hover:scale-105">
            <RefreshCw size={13} /> Làm mới
          </button>
          <button className="flex items-center gap-1.5 px-3.5 py-2.5 bg-gradient-to-r from-slate-600 to-slate-700 text-white rounded-xl text-xs font-semibold shadow-sm hover:opacity-90 transition-all hover:scale-105">
            <Download size={13} /> Xuất log
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Tổng sự kiện', value: counts.total, icon: Activity, gradient: '', bg: 'bg-slate-50', border: 'border-slate-100', color: 'text-slate-700', iconBg: 'bg-white border border-slate-200', iconColor: 'text-slate-900' },
          { label: 'Hôm nay', value: counts.today, icon: Clock, gradient: 'from-blue-500 to-indigo-500', bg: 'bg-blue-50', border: 'border-blue-100', color: 'text-blue-700' },
          { label: 'Cảnh báo', value: counts.warnings, icon: AlertTriangle, gradient: 'from-amber-400 to-orange-500', bg: 'bg-amber-50', border: 'border-amber-100', color: 'text-amber-700' },
          { label: 'Lỗi / Thất bại', value: counts.errors, icon: XCircle, gradient: 'from-red-400 to-rose-500', bg: 'bg-red-50', border: 'border-red-100', color: 'text-red-700' },
        ].map(stat => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className={`${stat.bg} border ${stat.border} rounded-2xl p-4 flex items-center gap-3 hover:shadow-md transition-shadow`}>
              <div className={`w-10 h-10 rounded-xl ${stat.gradient ? `bg-gradient-to-br ${stat.gradient}` : stat.iconBg} flex items-center justify-center flex-shrink-0 shadow-sm`}>
                <Icon size={18} className={stat.iconColor || 'text-white'} />
              </div>
              <div>
                <div className={`text-xl font-bold ${stat.color}`}>{stat.value}</div>
                <div className="text-xs text-gray-500 font-medium">{stat.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-white/80 backdrop-blur rounded-2xl p-4 shadow-sm border border-white/60 space-y-3">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 flex-1">
            <Search size={15} className="text-gray-400 flex-shrink-0" />
            <input type="text" placeholder="Tìm theo ID, tài khoản, chi tiết..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
              className="bg-transparent text-sm text-gray-700 placeholder-gray-400 outline-none w-full" />
          </div>
          <div className="flex gap-2 flex-wrap">
            <select value={severityFilter} onChange={e => { setSeverityFilter(e.target.value); setPage(1); }}
              className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5 text-sm text-gray-700 outline-none cursor-pointer">
              <option>Tất cả</option>
              {Object.entries(severityLabels).map(([, v]) => <option key={v}>{v}</option>)}
            </select>
            <select value={dateFilter} onChange={e => { setDateFilter(e.target.value); setPage(1); }}
              className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5 text-sm text-gray-700 outline-none cursor-pointer">
              {['Tất cả', 'Hôm nay', 'Hôm qua'].map(d => <option key={d}>{d}</option>)}
            </select>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {['Tất cả', ...Object.values(actionConfig).map((v) => v.label)].map(f => (
            <button key={f} onClick={() => { setActionFilter(f); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${actionFilter === f ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-sm' : 'bg-gray-100 text-gray-500 hover:bg-emerald-50 hover:text-emerald-700'}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <div className="text-sm font-semibold text-gray-700">Nhật ký hệ thống</div>
          <span className="text-xs text-gray-400">Tìm thấy <span className="font-semibold text-gray-600">{filtered.length}</span> sự kiện</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/80">
                {['Mức độ', 'Mã log', 'Thời gian', 'Tài khoản', 'Hành động', 'Tài nguyên', 'Chi tiết', 'IP / Thiết bị', ''].map((h, i) => (
                  <th key={i} className={`text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap
                    ${i === 1 ? 'hidden xl:table-cell' : i === 5 ? 'hidden md:table-cell' : i === 6 ? 'hidden lg:table-cell' : i === 7 ? 'hidden xl:table-cell' : ''}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {paged.map(log => {
                const action = actionConfig[log.action];
                const AIcon = action.icon;
                const sev = severityConfig[log.severity];
                const SevIcon = sev.icon;
                return (
                  <tr key={log.id} className="hover:bg-slate-50/50 transition-colors cursor-pointer group" onClick={() => setSelectedLog(log)}>
                    <td className="px-4 py-3.5">
                      <div className={`w-8 h-8 rounded-lg ${sev.bg} flex items-center justify-center`}>
                        <SevIcon size={14} className={sev.color} />
                      </div>
                    </td>
                    <td className="px-4 py-3.5 hidden xl:table-cell">
                      <span className="font-mono text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded">{log.id}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="text-xs font-medium text-gray-700 whitespace-nowrap">{log.timestamp}</div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-slate-400 to-slate-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                          {log.account.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-xs font-semibold text-gray-700">{log.account}</div>
                          <div className="text-xs text-gray-400">{log.role}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg border whitespace-nowrap ${action.bg} ${action.color} ${action.border}`}>
                        <AIcon size={11} />{action.label}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 hidden md:table-cell">
                      <div className="text-xs font-medium text-gray-700">{log.resource}</div>
                      <div className="text-xs text-gray-400">#{log.resourceId}</div>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <div className="text-xs text-gray-600 max-w-[220px] truncate">{log.detail}</div>
                    </td>
                    <td className="px-4 py-3.5 hidden xl:table-cell">
                      <div className="flex items-center gap-1 text-xs text-gray-500">
                        <Globe size={11} className="flex-shrink-0" />
                        <span className="font-mono">{log.ip}</span>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-gray-400 mt-0.5">
                        <Monitor size={11} className="flex-shrink-0" />{log.browser}
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <button className="opacity-0 group-hover:opacity-100 text-xs text-slate-600 bg-slate-100 px-2.5 py-1.5 rounded-lg hover:bg-slate-200 transition-all font-semibold whitespace-nowrap">
                        Chi tiết
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between px-4 py-3.5 border-t border-gray-100 bg-gray-50/50">
          <span className="text-xs text-gray-400">
            Trang <span className="font-semibold text-gray-600">{page}</span> / {totalPages} · {filtered.length} sự kiện
          </span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400 hover:bg-slate-100 hover:text-slate-600 disabled:opacity-40 transition-colors">
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(p => (
              <button key={p} onClick={() => setPage(p)}
                className={`w-8 h-8 rounded-lg text-xs font-semibold transition-colors ${page === p ? 'bg-gradient-to-r from-slate-600 to-slate-700 text-white shadow-sm' : 'border border-gray-200 text-gray-500 hover:bg-slate-100 hover:text-slate-700'}`}>
                {p}
              </button>
            ))}
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400 hover:bg-slate-100 hover:text-slate-600 disabled:opacity-40 transition-colors">
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {selectedLog && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm" onClick={() => setSelectedLog(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 border border-gray-100" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-gray-900 font-semibold">Chi tiết nhật ký</h3>
                <span className="font-mono text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded mt-1 inline-block">{selectedLog.id}</span>
              </div>
              <button onClick={() => setSelectedLog(null)} className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center text-gray-400"><XCircle size={18} /></button>
            </div>

            <div className={`flex items-center gap-3 p-3 rounded-xl mb-4 ${severityConfig[selectedLog.severity].bg}`}>
              {(() => { const SevIcon = severityConfig[selectedLog.severity].icon; return <SevIcon size={18} className={severityConfig[selectedLog.severity].color} />; })()}
              <div>
                <div className={`text-sm font-semibold ${severityConfig[selectedLog.severity].color}`}>{severityLabels[selectedLog.severity]}</div>
                <div className="text-xs text-gray-500">{selectedLog.status === 'success' ? '✅ Thực hiện thành công' : '❌ Thực hiện thất bại'}</div>
              </div>
            </div>

            <div className="space-y-2.5">
              {[
                { icon: Clock, label: 'Thời gian', value: selectedLog.timestamp },
                { icon: User, label: 'Tài khoản', value: `${selectedLog.account} (${selectedLog.role})` },
                { icon: Activity, label: 'Hành động', value: actionConfig[selectedLog.action].label },
                { icon: Database, label: 'Tài nguyên', value: `${selectedLog.resource} #${selectedLog.resourceId}` },
                { icon: Globe, label: 'Địa chỉ IP', value: selectedLog.ip },
                { icon: Monitor, label: 'Thiết bị', value: `${selectedLog.device} · ${selectedLog.browser}` },
              ].map(row => {
                const Icon = row.icon;
                return (
                  <div key={row.label} className="flex items-start gap-3 py-2.5 border-b border-gray-50 last:border-0">
                    <Icon size={14} className="text-slate-400 flex-shrink-0 mt-0.5" />
                    <span className="text-xs text-gray-500 w-28 flex-shrink-0">{row.label}</span>
                    <span className="text-sm font-medium text-gray-700 flex-1">{row.value}</span>
                  </div>
                );
              })}
              <div className="flex items-start gap-3 py-2.5">
                <Info size={14} className="text-slate-400 flex-shrink-0 mt-0.5" />
                <span className="text-xs text-gray-500 w-28 flex-shrink-0">Chi tiết</span>
                <span className="text-sm text-gray-700 flex-1">{selectedLog.detail}</span>
              </div>
            </div>

            <button onClick={() => setSelectedLog(null)} className="w-full mt-5 px-4 py-2.5 bg-slate-700 text-white rounded-xl text-sm font-semibold hover:bg-slate-800 transition-colors">Đóng</button>
          </div>
        </div>
      )}
    </div>
  );
}
