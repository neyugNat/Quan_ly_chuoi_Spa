import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../lib/api';
import {
  Search, Plus, MapPin, User,
  CheckCircle2, XCircle, AlertCircle, ChevronLeft,
  ChevronRight, Phone, Filter,
} from 'lucide-react';

function formatMoneyVND(value: any) {
  const n = Number(value || 0);
  try {
    return `${new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(n)}đ`;
  } catch {
    return `${n}đ`;
  }
}

function formatDateDDMMYYYY(value: any) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '-';
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

function formatTimeHHMM(value: any) {
  if (!value) return '--:--';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '--:--';
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

function toUiStatus(status: string) {
  if (status === 'booked' || status === 'confirmed') return 'confirmed';
  if (status === 'arrived' || status === 'in_service') return 'pending';
  if (status === 'cancelled' || status === 'no_show') return 'cancelled';
  if (status === 'completed' || status === 'paid') return 'completed';
  return 'pending';
}

const statusConfig: Record<string, { label: string; color: string; bg: string; border: string; dot: string }> = {
  confirmed: { label: 'Xác nhận', color: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200', dot: 'bg-emerald-500' },
  pending: { label: 'Chờ xử lý', color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', dot: 'bg-amber-500' },
  cancelled: { label: 'Đã hủy', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', dot: 'bg-red-500' },
  completed: {
    label: 'Hoàn thành',
    color: 'text-cyan-800 dark:text-cyan-100',
    bg: 'bg-cyan-100 dark:bg-cyan-500/25',
    border: 'border-cyan-300 dark:border-cyan-300/60',
    dot: 'bg-cyan-600 dark:bg-cyan-300',
  },
};

const avatarColors = [
  'from-[#3b82f6] to-[#60a5fa]',
  'from-[#38bdf8] to-[#7dd3fc]',
  'from-[#60a5fa] to-[#93c5fd]',
  'from-[#0ea5e9] to-[#38bdf8]',
  'from-[#3b82f6] to-[#93c5fd]',
];

const filters = ['Tất cả', 'Xác nhận', 'Chờ xử lý', 'Đã hủy', 'Hoàn thành'];

export function Appointments() {
  const [appointments, setAppointments] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('Tất cả');
  const [branch, setBranch] = useState('Tất cả chi nhánh');
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        const [appointmentRes, customerRes, serviceRes, staffRes] = await Promise.all([
          apiFetch('/api/appointments'),
          apiFetch('/api/customers'),
          apiFetch('/api/services'),
          apiFetch('/api/staffs'),
        ]);

        const appointmentRows = appointmentRes?.items || [];
        const customerRows = customerRes?.items || [];
        const serviceRows = serviceRes?.items || [];
        const staffRows = staffRes?.items || [];

        let branchRows: any[] = [];
        try {
          const branchesRes = await apiFetch('/api/branches');
          branchRows = branchesRes?.items || [];
        } catch {
          branchRows = [];
        }

        const customerById = new Map<number, any>();
        customerRows.forEach((c: any) => customerById.set(Number(c?.id), c));

        const serviceById = new Map<number, any>();
        serviceRows.forEach((s: any) => serviceById.set(Number(s?.id), s));

        const staffById = new Map<number, any>();
        staffRows.forEach((s: any) => staffById.set(Number(s?.id), s));

        const branchById = new Map<number, any>();
        branchRows.forEach((b: any) => branchById.set(Number(b?.id), b));

        const mapped = appointmentRows.map((apt: any) => {
          const customer = customerById.get(Number(apt?.customer_id));
          const service = serviceById.get(Number(apt?.service_id));
          const staff = staffById.get(Number(apt?.staff_id));
          const branchRow = branchById.get(Number(apt?.branch_id));
          const uiStatus = toUiStatus(String(apt?.status || 'pending'));

          return {
            id: Number(apt?.id || 0),
            customer: customer?.full_name || `Khách #${apt?.customer_id || ''}`,
            phone: customer?.phone || '-',
            service: service?.name || 'Chưa gán dịch vụ',
            time: formatTimeHHMM(apt?.start_time),
            date: formatDateDDMMYYYY(apt?.start_time),
            branch: branchRow?.name || `CN #${apt?.branch_id || ''}`,
            staff: staff?.full_name || 'Chưa phân công',
            price: formatMoneyVND(service?.price || 0),
            status: uiStatus,
          };
        });

        if (mounted) setAppointments(mapped);
      } catch {
        if (mounted) setAppointments([]);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  const branches = useMemo(() => {
    const list = Array.from(new Set(appointments.map((a) => a.branch).filter(Boolean)));
    return ['Tất cả chi nhánh', ...list];
  }, [appointments]);

  const filtered = appointments.filter((a) => {
    const matchSearch = a.customer.toLowerCase().includes(search.toLowerCase()) || a.service.toLowerCase().includes(search.toLowerCase());
    const matchFilter = activeFilter === 'Tất cả' || statusConfig[a.status]?.label === activeFilter;
    const matchBranch = branch === 'Tất cả chi nhánh' || a.branch === branch;
    return matchSearch && matchFilter && matchBranch;
  });

  const counts = {
    total: appointments.length,
    confirmed: appointments.filter(a => a.status === 'confirmed').length,
    pending: appointments.filter(a => a.status === 'pending').length,
    cancelled: appointments.filter(a => a.status === 'cancelled').length,
    completed: appointments.filter(a => a.status === 'completed').length,
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-[#64748b] text-sm">Quản lý toàn bộ lịch hẹn trong chuỗi</p>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-[#1d4ed8] to-[#3b82f6] text-white px-4 py-2.5 rounded-xl hover:opacity-90 transition-opacity text-sm font-medium shadow-md shadow-blue-200"
        >
          <Plus size={16} /> Thêm lịch hẹn
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Tổng lịch hẹn', value: counts.total, color: 'text-[#3b82f6]', bg: 'bg-blue-50', border: 'border-blue-100' },
          { label: 'Xác nhận', value: counts.confirmed, color: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-100' },
          { label: 'Chờ xử lý', value: counts.pending, color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-100' },
          { label: 'Đã hủy', value: counts.cancelled, color: 'text-red-500', bg: 'bg-red-50', border: 'border-red-100' },
        ].map((item) => (
          <div key={item.label} className={`${item.bg} border ${item.border} rounded-xl p-4`}>
            <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
            <div className="text-xs text-[#64748b] font-medium mt-0.5">{item.label}</div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#dbeafe]">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="flex items-center gap-2 bg-[#eff6ff] border border-[#bfdbfe] rounded-xl px-3 py-2.5 flex-1">
            <Search size={15} className="text-[#93c5fd] flex-shrink-0" />
            <input
              type="text"
              placeholder="Tìm khách hàng, dịch vụ..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent text-sm text-[#1e3a8a] placeholder-[#93c5fd] outline-none w-full"
            />
          </div>
          <div className="flex items-center gap-2 bg-[#eff6ff] border border-[#bfdbfe] rounded-xl px-3 py-2.5">
            <Filter size={14} className="text-[#93c5fd]" />
            <select
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              className="bg-transparent text-sm text-[#1e3a8a] outline-none cursor-pointer"
            >
              {branches.map((b) => <option key={b}>{b}</option>)}
            </select>
          </div>
        </div>
        <div className="flex gap-2 mt-3 flex-wrap">
          {filters.map((f) => (
            <button
              key={f}
              onClick={() => setActiveFilter(f)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${activeFilter === f ? 'bg-[#3b82f6] text-white shadow-sm' : 'bg-[#eff6ff] text-[#475569] hover:bg-[#dbeafe] hover:text-[#3b82f6]'}`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-[#dbeafe] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#dbeafe] bg-[#eff6ff]">
                {['Khách hàng', 'Dịch vụ', 'Thời gian', 'Chi nhánh', 'Nhân viên', 'Giá', 'Trạng thái', ''].map((h, i) => (
                  <th key={i} className={`text-left px-4 py-3.5 text-xs font-semibold text-[#64748b] uppercase tracking-wider ${i === 1 ? 'hidden md:table-cell' : i === 3 ? 'hidden lg:table-cell' : i === 4 ? 'hidden xl:table-cell' : i === 5 ? 'hidden md:table-cell' : ''}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#eff6ff]">
              {filtered.map((apt, idx) => {
                const s = statusConfig[apt.status] || statusConfig.pending;
                return (
                  <tr key={apt.id} className="hover:bg-[#eff6ff] transition-colors">
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-full bg-gradient-to-br ${avatarColors[idx % avatarColors.length]} flex items-center justify-center text-white text-xs font-bold flex-shrink-0`}>
                          {apt.customer.charAt(0)}
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-[#1e3a8a]">{apt.customer}</div>
                          <div className="text-xs text-[#94a3b8] flex items-center gap-1"><Phone size={9} />{apt.phone}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 hidden md:table-cell">
                      <div className="text-sm text-[#475569] max-w-[180px] truncate">{apt.service}</div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="text-sm font-semibold text-[#1e3a8a]">{apt.time}</div>
                      <div className="text-xs text-[#94a3b8]">{apt.date}</div>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <span className="flex items-center gap-1 text-xs text-[#475569]"><MapPin size={11} className="text-[#60a5fa]" />{apt.branch}</span>
                    </td>
                    <td className="px-4 py-3.5 hidden xl:table-cell">
                      <span className="flex items-center gap-1 text-xs text-[#475569]"><User size={11} className="text-[#60a5fa]" />{apt.staff}</span>
                    </td>
                    <td className="px-4 py-3.5 hidden md:table-cell">
                      <div className="text-sm font-bold text-[#3b82f6]">{apt.price}</div>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg border ${s.bg} ${s.color} ${s.border}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                        <span className="hidden sm:inline">{s.label}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <button className="text-xs font-semibold text-[#3b82f6] bg-blue-50 px-3 py-1.5 rounded-lg hover:bg-blue-100 transition-colors">Chi tiết</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between px-4 py-3.5 border-t border-[#dbeafe] bg-[#eff6ff]">
          <span className="text-xs text-[#94a3b8]">Hiển thị <span className="font-semibold text-[#475569]">{filtered.length}</span> / {appointments.length} lịch hẹn</span>
          <div className="flex items-center gap-1">
            <button className="w-8 h-8 rounded-lg border border-[#bfdbfe] flex items-center justify-center text-[#94a3b8] hover:bg-[#dbeafe] hover:text-[#3b82f6] transition-colors"><ChevronLeft size={14} /></button>
            <button className="w-8 h-8 rounded-lg bg-[#3b82f6] text-white text-xs font-semibold shadow-sm">1</button>
            <button className="w-8 h-8 rounded-lg border border-[#bfdbfe] text-xs text-[#475569] hover:bg-[#dbeafe] hover:text-[#3b82f6] transition-colors">2</button>
            <button className="w-8 h-8 rounded-lg border border-[#bfdbfe] flex items-center justify-center text-[#94a3b8] hover:bg-[#dbeafe] hover:text-[#3b82f6] transition-colors"><ChevronRight size={14} /></button>
          </div>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-[#dbeafe]">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-[#1e3a8a]">Thêm lịch hẹn mới</h3>
                <p className="text-[#94a3b8] text-xs mt-0.5">Điền thông tin bên dưới</p>
              </div>
              <button onClick={() => setShowModal(false)} className="w-8 h-8 rounded-lg hover:bg-[#eff6ff] flex items-center justify-center text-[#94a3b8]"><XCircle size={18} /></button>
            </div>
            <div className="space-y-3">
              {[{ label: 'Tên khách hàng', placeholder: 'Nhập tên khách hàng' }, { label: 'Số điện thoại', placeholder: 'Nhập số điện thoại' }].map((f) => (
                <div key={f.label}>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">{f.label}</label>
                  <input className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] focus:ring-2 focus:ring-blue-100 bg-[#eff6ff] transition-all" placeholder={f.placeholder} />
                </div>
              ))}
              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Dịch vụ</label>
                <input className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff]" placeholder="Tên dịch vụ" />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowModal(false)} className="flex-1 px-4 py-2.5 border border-[#bfdbfe] rounded-xl text-sm text-[#475569] hover:bg-[#eff6ff] font-medium transition-colors">Hủy</button>
              <button onClick={() => setShowModal(false)} className="flex-1 px-4 py-2.5 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white rounded-xl text-sm font-semibold shadow-md shadow-blue-200">Xác nhận</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
