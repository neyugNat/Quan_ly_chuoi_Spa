import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../lib/api';
import { MapPin, Phone, Clock, Users, Star, Edit2, Plus, XCircle, CheckCircle2, Building2 } from 'lucide-react';

function formatMoneyM(value: any) {
  const n = Number(value || 0) / 1000000;
  if (!Number.isFinite(n)) return '0.0 tr';
  return `${n.toFixed(1)} tr`;
}

function formatMonthYear(value: any) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '-';
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  return `${mm}/${yyyy}`;
}

function parseHoursParts(input: any) {
  const fallback = { open: '08:00', close: '22:00' };
  if (!input) return fallback;
  try {
    const obj = typeof input === 'string' ? JSON.parse(input) : input;
    const open = String(obj?.open || '').trim();
    const close = String(obj?.close || '').trim();
    if (!open || !close) return fallback;
    return { open, close };
  } catch {
    return fallback;
  }
}

const images = [
  'https://images.unsplash.com/photo-1633526543913-d30e3c230d1f?w=400&q=80',
  'https://images.unsplash.com/photo-1700142360825-d21edc53c8db?w=400&q=80',
  'https://images.unsplash.com/photo-1633526543913-d30e3c230d1f?w=400&q=80',
  'https://images.unsplash.com/photo-1700142360825-d21edc53c8db?w=400&q=80',
  'https://images.unsplash.com/photo-1633526543913-d30e3c230d1f?w=400&q=80',
];

export function Branches() {
  const [branches, setBranches] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingBranchId, setEditingBranchId] = useState<number | null>(null);
  const [savingBranch, setSavingBranch] = useState(false);
  const [branchFormError, setBranchFormError] = useState('');
  const [branchForm, setBranchForm] = useState({
    name: '',
    address: '',
    status: 'active',
    openTime: '08:00',
    closeTime: '22:00',
  });

  function resetBranchForm() {
    setBranchForm({
      name: '',
      address: '',
      status: 'active',
      openTime: '08:00',
      closeTime: '22:00',
    });
    setBranchFormError('');
    setSavingBranch(false);
  }

  function openCreateModal() {
    setIsEditMode(false);
    setEditingBranchId(null);
    setSelected(null);
    resetBranchForm();
    setShowModal(true);
  }

  function openEditModal(branch: any) {
    const hourParts = parseHoursParts(branch?.workingHoursJson);
    setIsEditMode(true);
    setEditingBranchId(Number(branch?.id || 0) || null);
    setSelected(null);
    setBranchForm({
      name: String(branch?.name || ''),
      address: String(branch?.address || ''),
      status: String(branch?.status || 'active') === 'inactive' ? 'inactive' : 'active',
      openTime: hourParts.open,
      closeTime: hourParts.close,
    });
    setBranchFormError('');
    setSavingBranch(false);
    setShowModal(true);
  }

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        const branchRes = await apiFetch('/api/branches');
        const branchRows = branchRes?.items || [];

        const mapped = await Promise.all(
          branchRows.map(async (branch: any, idx: number) => {
            try {
              const hourParts = parseHoursParts(branch?.working_hours_json);
              const headers = { 'X-Branch-Id': String(branch.id) };
              const [staffRes, revenueRes, appointmentRes] = await Promise.all([
                apiFetch('/api/staffs', { headers }),
                apiFetch('/api/reports/revenue', { headers }),
                apiFetch('/api/reports/appointments', { headers }),
              ]);

              const staffCount = (staffRes?.items || []).length;
              const revenueValue = (revenueRes?.items || []).reduce((sum: number, row: any) => sum + Number(row?.revenue || 0), 0);
              const appointmentCount = (appointmentRes?.items || []).reduce((sum: number, row: any) => sum + Number(row?.total || 0), 0);

              return {
                id: Number(branch?.id || 0),
                name: branch?.name || `Chi nhánh #${branch?.id}`,
                short: `CN ${branch?.id}`,
                address: branch?.address || '-',
                phone: '-',
                hours: `${hourParts.open} - ${hourParts.close}`,
                manager: '-',
                staff: staffCount,
                rooms: '-',
                rating: '-',
                revenue: formatMoneyM(revenueValue),
                appointments: appointmentCount,
                established: formatMonthYear(branch?.created_at),
                image: images[idx % images.length],
                status: branch?.status || 'active',
                workingHoursJson: branch?.working_hours_json || JSON.stringify(hourParts),
              };
            } catch {
              const hourParts = parseHoursParts(branch?.working_hours_json);
              return {
                id: Number(branch?.id || 0),
                name: branch?.name || `Chi nhánh #${branch?.id}`,
                short: `CN ${branch?.id}`,
                address: branch?.address || '-',
                phone: '-',
                hours: `${hourParts.open} - ${hourParts.close}`,
                manager: '-',
                staff: 0,
                rooms: '-',
                rating: '-',
                revenue: '0.0 tr',
                appointments: 0,
                established: formatMonthYear(branch?.created_at),
                image: images[idx % images.length],
                status: branch?.status || 'active',
                workingHoursJson: branch?.working_hours_json || JSON.stringify(hourParts),
              };
            }
          }),
        );

        if (mounted) setBranches(mapped);
      } catch {
        if (mounted) setBranches([]);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  async function submitBranchForm() {
    const name = branchForm.name.trim();
    if (!name) {
      setBranchFormError('Vui lòng nhập tên chi nhánh.');
      return;
    }

    const open = branchForm.openTime.trim() || '08:00';
    const close = branchForm.closeTime.trim() || '22:00';
    const status = branchForm.status === 'inactive' ? 'inactive' : 'active';
    const workingHoursJson = JSON.stringify({ open, close });
    const payload = {
      name,
      address: branchForm.address.trim() || null,
      status,
      working_hours_json: workingHoursJson,
    };

    setSavingBranch(true);
    setBranchFormError('');

    try {
      if (isEditMode && editingBranchId) {
        const updated = await apiFetch(`/api/branches/${editingBranchId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        });

        const parsed = parseHoursParts(updated?.working_hours_json || workingHoursJson);
        setBranches((prev) =>
          prev.map((branch) =>
            branch.id === editingBranchId
              ? {
                  ...branch,
                  name: updated?.name || name,
                  address: updated?.address || '-',
                  status: updated?.status || status,
                  hours: `${parsed.open} - ${parsed.close}`,
                  workingHoursJson: updated?.working_hours_json || workingHoursJson,
                }
              : branch,
          ),
        );
        setSelected((prev) =>
          prev && prev.id === editingBranchId
            ? {
                ...prev,
                name: updated?.name || name,
                address: updated?.address || '-',
                status: updated?.status || status,
                hours: `${parsed.open} - ${parsed.close}`,
                workingHoursJson: updated?.working_hours_json || workingHoursJson,
              }
            : prev,
        );
      } else {
        const created = await apiFetch('/api/branches', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        const parsed = parseHoursParts(created?.working_hours_json || workingHoursJson);
        setBranches((prev) => [
          {
            id: Number(created?.id || 0),
            name: created?.name || name,
            short: `CN ${created?.id}`,
            address: created?.address || '-',
            phone: '-',
            hours: `${parsed.open} - ${parsed.close}`,
            manager: '-',
            staff: 0,
            rooms: '-',
            rating: '-',
            revenue: '0.0 tr',
            appointments: 0,
            established: formatMonthYear(created?.created_at),
            image: images[prev.length % images.length],
            status: created?.status || status,
            workingHoursJson: created?.working_hours_json || workingHoursJson,
          },
          ...prev,
        ]);
      }

      setShowModal(false);
      resetBranchForm();
    } catch (error: any) {
      if (error?.status === 403) {
        setBranchFormError('Bạn không có quyền sửa chi nhánh (cần super_admin).');
      } else if (error?.status === 400) {
        setBranchFormError('Dữ liệu chưa hợp lệ. Vui lòng kiểm tra lại.');
      } else {
        setBranchFormError('Không thể lưu chi nhánh lúc này. Vui lòng thử lại.');
      }
    } finally {
      setSavingBranch(false);
    }
  }

  const totalStaff = useMemo(() => branches.reduce((a, b) => a + Number(b.staff || 0), 0), [branches]);
  const totalRooms = useMemo(() => branches.reduce((a, b) => a + (Number(b.rooms) || 0), 0), [branches]);
  const avgRating = useMemo(() => {
    const withRating = branches.filter((b) => Number(b.rating) > 0);
    if (!withRating.length) return 'N/A';
    return (withRating.reduce((a, b) => a + Number(b.rating), 0) / withRating.length).toFixed(1);
  }, [branches]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-[#64748b] text-sm">Quản lý thông tin các chi nhánh trong chuỗi</p>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white px-4 py-2.5 rounded-xl hover:opacity-90 text-sm font-medium shadow-md shadow-blue-200"
        >
          <Plus size={16} /> Mở chi nhánh mới
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Chi nhánh hoạt động', value: branches.filter((b) => b.status === 'active').length, color: 'text-[#1d4ed8]', bg: 'bg-blue-50', border: 'border-blue-100' },
          { label: 'Tổng nhân viên', value: totalStaff, color: 'text-indigo-700', bg: 'bg-indigo-50', border: 'border-indigo-100' },
          { label: 'Tổng phòng trị liệu', value: totalRooms || '-', color: 'text-cyan-700', bg: 'bg-cyan-50', border: 'border-cyan-100' },
          { label: 'Đánh giá trung bình', value: avgRating === 'N/A' ? 'N/A' : `${avgRating} ★`, color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-100' },
        ].map((item) => (
          <div key={item.label} className={`${item.bg} border ${item.border} rounded-xl p-4`}>
            <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
            <div className="text-xs text-[#64748b] font-medium mt-0.5">{item.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {branches.map((branch, idx) => (
          <div
            key={branch.id}
            className="bg-white rounded-2xl shadow-sm border border-[#e8eef8] overflow-hidden hover:shadow-md hover:border-[#bfdbfe] transition-all cursor-pointer"
            onClick={() => setSelected(branch)}
          >
            <div className="relative h-44 overflow-hidden">
              <img src={branch.image} alt={branch.name} className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-[#0c1e40]/80 via-[#0c1e40]/20 to-transparent" />
              <div className="absolute top-3 left-3 w-8 h-8 rounded-lg bg-[#1d4ed8] flex items-center justify-center text-white text-xs font-bold shadow">
                {idx + 1}
              </div>
              <div className={`absolute top-3 right-3 flex items-center gap-1 text-white text-xs font-semibold px-2.5 py-1 rounded-full shadow ${branch.status === 'active' ? 'bg-emerald-500' : 'bg-slate-500'}`}>
                <CheckCircle2 size={10} /> {branch.status === 'active' ? 'Hoạt động' : 'Tạm ngưng'}
              </div>
              <div className="absolute bottom-3 left-4 right-4">
                <h3 className="text-white font-semibold">{branch.name}</h3>
                <div className="flex items-center gap-3 mt-1">
                  <span className="flex items-center gap-1 text-white/80 text-xs"><Star size={10} className="fill-amber-400 text-amber-400" />{branch.rating}</span>
                  <span className="text-white/60 text-xs">•</span>
                  <span className="text-white/80 text-xs">Từ {branch.established}</span>
                </div>
              </div>
            </div>
            <div className="p-4">
              <div className="space-y-1.5 mb-4">
                <div className="flex items-start gap-2 text-xs text-[#475569]">
                  <MapPin size={12} className="text-[#3b82f6] mt-0.5 flex-shrink-0" />
                  <span className="leading-relaxed">{branch.address}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1.5 text-xs text-[#475569]"><Phone size={11} className="text-[#3b82f6]" />{branch.phone}</span>
                  <span className="flex items-center gap-1.5 text-xs text-[#475569]"><Clock size={11} className="text-[#3b82f6]" />{branch.hours}</span>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-2 mb-4">
                {[
                  { label: 'NV', value: branch.staff },
                  { label: 'Phòng', value: branch.rooms },
                  { label: 'Lịch hẹn', value: branch.appointments },
                  { label: 'DT', value: branch.revenue },
                ].map((stat, i) => (
                  <div key={i} className="text-center bg-[#f8faff] border border-[#e8eef8] rounded-xl py-2">
                    <div className="text-xs font-bold text-[#0c1e40]">{stat.value}</div>
                    <div className="text-xs text-[#94a3b8]" style={{ fontSize: '10px' }}>{stat.label}</div>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-[#f0f4fb]">
                <span className="text-xs text-[#94a3b8]">
                  Quản lý: <span className="text-[#0c1e40] font-semibold">{branch.manager}</span>
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    openEditModal(branch);
                  }}
                  className="flex items-center gap-1.5 text-xs text-[#1d4ed8] font-semibold bg-blue-50 px-3 py-1.5 rounded-lg hover:bg-blue-100 transition-all duration-200 hover:-translate-y-0.5 hover:brightness-110 hover:shadow-md hover:shadow-blue-200 active:translate-y-0"
                >
                  <Edit2 size={11} /> Chỉnh sửa
                </button>
              </div>
            </div>
          </div>
        ))}

        <div
          className="border-2 border-dashed border-[#bfdbfe] rounded-2xl flex flex-col items-center justify-center p-10 cursor-pointer hover:border-[#1d4ed8] hover:bg-[#f0f4fb] transition-all group"
          onClick={openCreateModal}
        >
          <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-[#bfdbfe] flex items-center justify-center mb-3 group-hover:bg-blue-100 transition-colors">
            <Building2 size={24} className="text-[#1d4ed8]" />
          </div>
          <div className="text-sm font-semibold text-[#1d4ed8]">Mở chi nhánh mới</div>
          <div className="text-xs text-[#94a3b8] mt-1">Mở rộng chuỗi Lotus Spa</div>
        </div>
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden border border-[#e8eef8]">
            <div className="relative h-48">
              <img src={selected.image} alt={selected.name} className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-[#0c1e40]/80 to-transparent" />
              <button
                onClick={() => setSelected(null)}
                className="absolute top-3 right-3 w-8 h-8 rounded-lg bg-white/20 backdrop-blur flex items-center justify-center text-white hover:bg-white/40 transition-colors"
              >
                <XCircle size={18} />
              </button>
              <div className="absolute bottom-4 left-5">
                <h2 className="text-white">{selected.name}</h2>
                <div className="flex items-center gap-1.5 text-white/80 text-xs mt-0.5">
                  <Star size={10} className="fill-amber-400 text-amber-400" /> {selected.rating}
                  <span className="text-white/50">•</span>
                  {selected.status === 'active' ? 'Hoạt động' : 'Tạm ngưng'} từ {selected.established}
                </div>
              </div>
            </div>
            <div className="p-5">
              <div className="grid grid-cols-2 gap-3 mb-4">
                {[
                  { label: 'Nhân viên', value: `${selected.staff} người` },
                  { label: 'Phòng trị liệu', value: selected.rooms },
                  { label: 'Lịch hẹn tháng', value: selected.appointments },
                  { label: 'Doanh thu tháng', value: selected.revenue },
                ].map((item) => (
                  <div key={item.label} className="bg-[#f8faff] border border-[#e8eef8] rounded-xl p-3">
                    <div className="text-sm font-bold text-[#1d4ed8]">{item.value}</div>
                    <div className="text-xs text-[#94a3b8] mt-0.5">{item.label}</div>
                  </div>
                ))}
              </div>
              <div className="space-y-2.5 text-sm">
                <div className="flex items-start gap-2.5"><MapPin size={15} className="text-[#3b82f6] mt-0.5 flex-shrink-0" /><span className="text-[#475569]">{selected.address}</span></div>
                <div className="flex items-center gap-2.5"><Phone size={15} className="text-[#3b82f6]" /><span className="text-[#475569]">{selected.phone}</span></div>
                <div className="flex items-center gap-2.5"><Clock size={15} className="text-[#3b82f6]" /><span className="text-[#475569]">{selected.hours}</span></div>
                <div className="flex items-center gap-2.5"><Users size={15} className="text-[#3b82f6]" /><span className="text-[#475569]">Quản lý: <span className="font-semibold text-[#0c1e40]">{selected.manager}</span></span></div>
              </div>
              <div className="flex gap-3 mt-5">
                <button onClick={() => setSelected(null)} className="flex-1 px-4 py-2.5 border border-[#dbe4f5] rounded-xl text-sm text-[#475569] hover:bg-[#f0f4fb] font-medium">Đóng</button>
                <button
                  onClick={() => openEditModal(selected)}
                  className="flex-1 px-4 py-2.5 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white rounded-xl text-sm font-semibold shadow-md shadow-blue-200 transition-all duration-200 hover:-translate-y-0.5 hover:brightness-110 hover:shadow-lg hover:shadow-blue-300 active:translate-y-0"
                >
                  Chỉnh sửa
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-[#dbeafe]">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-[#1e3a8a]">{isEditMode ? 'Chỉnh sửa chi nhánh' : 'Mở chi nhánh mới'}</h3>
                <p className="text-[#94a3b8] text-xs mt-0.5">
                  {isEditMode ? 'Cập nhật thông tin chi nhánh đang chọn' : 'Điền thông tin chi nhánh'}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowModal(false);
                  resetBranchForm();
                }}
                className="w-8 h-8 rounded-lg hover:bg-[#eff6ff] flex items-center justify-center text-[#94a3b8]"
              >
                <XCircle size={18} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Tên chi nhánh</label>
                <input
                  value={branchForm.name}
                  onChange={(e) => setBranchForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] focus:ring-2 focus:ring-blue-100 bg-[#eff6ff]"
                  placeholder="Nhập tên chi nhánh"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Địa chỉ</label>
                <input
                  value={branchForm.address}
                  onChange={(e) => setBranchForm((prev) => ({ ...prev, address: e.target.value }))}
                  className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] focus:ring-2 focus:ring-blue-100 bg-[#eff6ff]"
                  placeholder="Nhập địa chỉ"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Giờ mở</label>
                  <input
                    value={branchForm.openTime}
                    onChange={(e) => setBranchForm((prev) => ({ ...prev, openTime: e.target.value }))}
                    className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] focus:ring-2 focus:ring-blue-100 bg-[#eff6ff]"
                    placeholder="08:00"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Giờ đóng</label>
                  <input
                    value={branchForm.closeTime}
                    onChange={(e) => setBranchForm((prev) => ({ ...prev, closeTime: e.target.value }))}
                    className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] focus:ring-2 focus:ring-blue-100 bg-[#eff6ff]"
                    placeholder="22:00"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Trạng thái</label>
                <select
                  value={branchForm.status}
                  onChange={(e) => setBranchForm((prev) => ({ ...prev, status: e.target.value }))}
                  className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] focus:ring-2 focus:ring-blue-100 bg-[#eff6ff]"
                >
                  <option value="active">Hoạt động</option>
                  <option value="inactive">Tạm ngưng</option>
                </select>
              </div>
              {branchFormError && (
                <div className="text-xs text-red-500 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {branchFormError}
                </div>
              )}
            </div>
            <div className="flex gap-3 mt-5">
              <button
                onClick={() => {
                  setShowModal(false);
                  resetBranchForm();
                }}
                className="flex-1 px-4 py-2.5 border border-[#bfdbfe] rounded-xl text-sm text-[#475569] hover:bg-[#eff6ff] font-medium transition-all duration-200 hover:-translate-y-0.5 hover:brightness-105 hover:shadow-md hover:shadow-blue-100 active:translate-y-0"
                disabled={savingBranch}
              >
                Hủy
              </button>
              <button
                onClick={submitBranchForm}
                className="flex-1 px-4 py-2.5 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white rounded-xl text-sm font-semibold shadow-md shadow-blue-200 transition-all duration-200 hover:-translate-y-0.5 hover:brightness-110 hover:shadow-lg hover:shadow-blue-300 active:translate-y-0 disabled:opacity-60"
                disabled={savingBranch}
              >
                {savingBranch ? 'Đang lưu...' : isEditMode ? 'Lưu thay đổi' : 'Thêm chi nhánh'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
