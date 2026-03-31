import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../lib/api';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Users, CalendarDays, Download } from 'lucide-react';

function dateToIso(value: Date) {
  const y = value.getFullYear();
  const m = String(value.getMonth() + 1).padStart(2, '0');
  const d = String(value.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function buildPeriodRange(period: string) {
  const now = new Date();
  const to = dateToIso(now);

  if (period === 'Tháng này') {
    const from = new Date(now.getFullYear(), now.getMonth(), 1);
    return { from: dateToIso(from), to };
  }

  if (period === 'Quý này') {
    const quarterStartMonth = Math.floor(now.getMonth() / 3) * 3;
    const from = new Date(now.getFullYear(), quarterStartMonth, 1);
    return { from: dateToIso(from), to };
  }

  if (period === '6 tháng') {
    const from = new Date(now);
    from.setDate(from.getDate() - 180);
    return { from: dateToIso(from), to };
  }

  const from = new Date(now.getFullYear(), 0, 1);
  return { from: dateToIso(from), to };
}

function formatMoney(value: any) {
  const n = Number(value || 0);
  try {
    return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(n);
  } catch {
    return String(n);
  }
}

function formatMoneyM(value: any) {
  const n = Number(value || 0) / 1000000;
  return `${n.toFixed(1)} tr`;
}

function toMonthKey(day: string) {
  return String(day || '').slice(0, 7);
}

function toMonthLabel(monthKey: string) {
  const month = Number(String(monthKey || '').slice(5, 7) || 0);
  return month ? `T${month}` : monthKey;
}

function monthToKey(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  return `${y}-${m}`;
}

function buildRecentMonthKeys(count: number, anchorDate = new Date()) {
  const keys: string[] = [];
  const anchor = new Date(anchorDate.getFullYear(), anchorDate.getMonth(), 1);
  for (let offset = count - 1; offset >= 0; offset -= 1) {
    const d = new Date(anchor.getFullYear(), anchor.getMonth() - offset, 1);
    keys.push(monthToKey(d));
  }
  return keys;
}

const periods = ['Tháng này', 'Quý này', '6 tháng', 'Năm nay'];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-[#e2eaff] rounded-xl shadow-lg p-3 text-xs">
        <p className="font-semibold text-[#0c1e40] mb-1.5">{label}</p>
        {payload.map((p: any, i: number) => (
          <p key={i} style={{ color: p.color }} className="mb-0.5">
            {p.name}: <span className="font-semibold">{p.value} tr</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export function Reports() {
  const [period, setPeriod] = useState('Năm nay');
  const [revenueItems, setRevenueItems] = useState<any[]>([]);
  const [appointmentItems, setAppointmentItems] = useState<any[]>([]);
  const [appointmentList, setAppointmentList] = useState<any[]>([]);
  const [allAppointments, setAllAppointments] = useState<any[]>([]);
  const [serviceItems, setServiceItems] = useState<any[]>([]);
  const [branchRevenue, setBranchRevenue] = useState<any[]>([]);

  useEffect(() => {
    let mounted = true;

    async function load() {
      const { from, to } = buildPeriodRange(period);
      const query = `?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;

      try {
        const [revenueRes, appointmentRes, serviceRes, appointmentListRes] = await Promise.all([
          apiFetch(`/api/reports/revenue${query}`),
          apiFetch(`/api/reports/appointments${query}`),
          apiFetch('/api/services'),
          apiFetch('/api/appointments'),
        ]);

        if (!mounted) return;
        setRevenueItems(revenueRes?.items || []);
        setAppointmentItems(appointmentRes?.items || []);
        setServiceItems(serviceRes?.items || []);
        const allRows = appointmentListRes?.items || [];
        setAllAppointments(allRows);
        setAppointmentList(allRows.filter((row: any) => {
          const day = String(row?.start_time || '').slice(0, 10);
          return day >= from && day <= to;
        }));
      } catch {
        if (!mounted) return;
        setRevenueItems([]);
        setAppointmentItems([]);
        setServiceItems([]);
        setAppointmentList([]);
        setAllAppointments([]);
      }

      try {
        const branchesRes = await apiFetch('/api/branches');
        const branches = branchesRes?.items || [];
        const { from: f, to: t } = buildPeriodRange(period);
        const queryBranch = `?from=${encodeURIComponent(f)}&to=${encodeURIComponent(t)}`;

        const revenueRows = await Promise.all(
          branches.slice(0, 5).map(async (branch: any) => {
            try {
              const headers = { 'X-Branch-Id': String(branch.id) };
              const revenueRes = await apiFetch(`/api/reports/revenue${queryBranch}`, { headers });
              const revenueTotal = (revenueRes?.items || []).reduce((sum: number, it: any) => sum + Number(it?.revenue || 0), 0);
              return { name: branch?.name || `CN #${branch?.id}`, revenue: Math.round(revenueTotal / 1000000) };
            } catch {
              return null;
            }
          }),
        );

        if (mounted) {
          const resolved = revenueRows.filter(Boolean).sort((a: any, b: any) => Number(b?.revenue || 0) - Number(a?.revenue || 0));
          setBranchRevenue(resolved);
        }
      } catch {
        if (mounted) {
          const revenueTotal = revenueItems.reduce((sum, it) => sum + Number(it?.revenue || 0), 0);
          setBranchRevenue([{ name: 'Chi nhánh hiện tại', revenue: Math.round(revenueTotal / 1000000) }]);
        }
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, [period]);

  const monthlyRevenue = useMemo(() => {
    const byMonth = new Map<string, number>();
    revenueItems.forEach((row: any) => {
      const monthKey = toMonthKey(row?.day || '');
      if (!monthKey) return;
      byMonth.set(monthKey, (byMonth.get(monthKey) || 0) + Number(row?.revenue || 0));
    });

    return Array.from(byMonth.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([month, revenue]) => ({
        month: toMonthLabel(month),
        revenue: Math.round(revenue / 1000000),
        expenses: 0,
        profit: Math.round(revenue / 1000000),
      }));
  }, [revenueItems]);

  const serviceNameById = useMemo(() => {
    const map = new Map<number, string>();
    serviceItems.forEach((s: any) => map.set(Number(s?.id), s?.name || `Dịch vụ #${s?.id}`));
    return map;
  }, [serviceItems]);

  const serviceRevenue = useMemo(() => {
    const colorPalette = ['#1d4ed8', '#4f46e5', '#0891b2', '#0369a1', '#1e40af'];
    const byService = new Map<number, number>();
    revenueItems.forEach((row: any) => {
      const serviceId = Number(row?.service_id || 0);
      if (!serviceId) return;
      byService.set(serviceId, (byService.get(serviceId) || 0) + Number(row?.revenue || 0));
    });

    const rows = Array.from(byService.entries())
      .map(([serviceId, revenue]) => ({ serviceId, revenue }))
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 5);

    const total = rows.reduce((sum, row) => sum + row.revenue, 0);
    if (total <= 0) return [];

    return rows.map((row, idx) => ({
      name: serviceNameById.get(row.serviceId) || `DV #${row.serviceId}`,
      value: Math.max(1, Math.round((row.revenue / total) * 100)),
      color: colorPalette[idx % colorPalette.length],
    }));
  }, [revenueItems, serviceNameById]);

  const topServices = useMemo(() => {
    const bookingsByService = new Map<number, number>();
    appointmentList.forEach((apt: any) => {
      const serviceId = Number(apt?.service_id || 0);
      if (!serviceId) return;
      bookingsByService.set(serviceId, (bookingsByService.get(serviceId) || 0) + 1);
    });

    const revenueByService = new Map<number, number>();
    revenueItems.forEach((row: any) => {
      const serviceId = Number(row?.service_id || 0);
      if (!serviceId) return;
      revenueByService.set(serviceId, (revenueByService.get(serviceId) || 0) + Number(row?.revenue || 0));
    });

    const rows = Array.from(revenueByService.entries())
      .map(([serviceId, revenue]) => ({
        serviceId,
        name: serviceNameById.get(serviceId) || `Dịch vụ #${serviceId}`,
        bookings: bookingsByService.get(serviceId) || 0,
        revenue,
      }))
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 5);

    const total = rows.reduce((sum, row) => sum + row.revenue, 0);
    return rows.map((row) => ({
      name: row.name,
      bookings: row.bookings,
      revenue: `${formatMoney(row.revenue)}đ`,
      growth: total > 0 ? `+${Math.round((row.revenue / total) * 100)}%` : '0%',
    }));
  }, [appointmentList, revenueItems, serviceNameById]);

  const customerGrowth = useMemo(() => {
    const customerFirstMonth = new Map<number, string>();
    const recentMonthKeys = buildRecentMonthKeys(6, new Date());
    const recentMonthKeySet = new Set(recentMonthKeys);
    const monthlyActiveByCustomer = new Map<string, Set<number>>();
    recentMonthKeys.forEach((monthKey) => {
      monthlyActiveByCustomer.set(monthKey, new Set());
    });

    allAppointments.forEach((apt: any) => {
      const customerId = Number(apt?.customer_id || 0);
      const day = String(apt?.start_time || '').slice(0, 10);
      const monthKey = toMonthKey(day);
      if (!customerId || !monthKey) return;

      const prevFirst = customerFirstMonth.get(customerId);
      if (!prevFirst || monthKey < prevFirst) {
        customerFirstMonth.set(customerId, monthKey);
      }

      if (!recentMonthKeySet.has(monthKey)) return;
      monthlyActiveByCustomer.get(monthKey)?.add(customerId);
    });

    return recentMonthKeys.map((monthKey) => {
      const active = monthlyActiveByCustomer.get(monthKey) || new Set<number>();
      let newCount = 0;
      active.forEach((customerId) => {
        if (customerFirstMonth.get(customerId) === monthKey) newCount += 1;
      });
      const returning = Math.max(0, active.size - newCount);
      return {
        month: toMonthLabel(monthKey),
        new: newCount,
        returning,
      };
    });
  }, [allAppointments]);

  const revenueTotal = useMemo(() => revenueItems.reduce((sum, row) => sum + Number(row?.revenue || 0), 0), [revenueItems]);
  const apptTotal = useMemo(() => appointmentItems.reduce((sum, row) => sum + Number(row?.total || 0), 0), [appointmentItems]);
  const customerServed = useMemo(() => new Set(appointmentList.map((row: any) => Number(row?.customer_id || 0)).filter(Boolean)).size, [appointmentList]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-[#64748b] text-sm">Phân tích hiệu suất kinh doanh toàn chuỗi</p>
        <div className="flex items-center gap-2">
          <div className="flex bg-white border border-[#bfdbfe] rounded-xl overflow-hidden">
            {periods.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-2 text-xs font-medium transition-colors ${period === p ? 'bg-[#3b82f6] text-white' : 'text-[#64748b] hover:bg-[#eff6ff]'}`}
              >
                {p}
              </button>
            ))}
          </div>
          <button className="flex items-center gap-1.5 px-3.5 py-2 border border-[#bfdbfe] rounded-xl text-xs font-semibold text-[#3b82f6] hover:bg-[#eff6ff] bg-white transition-colors">
            <Download size={13} /> Xuất báo cáo
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: 'Tổng doanh thu', value: formatMoneyM(revenueTotal), sub: 'Theo backend', icon: DollarSign, change: '+0.0%', up: true, gradient: 'from-[#3b82f6] to-[#60a5fa]' },
          { label: 'Tổng lợi nhuận', value: 'N/A', sub: 'Thiếu dữ liệu chi phí', icon: TrendingUp, change: 'N/A', up: true, gradient: 'from-[#38bdf8] to-[#7dd3fc]' },
          { label: 'Khách hàng phục vụ', value: customerServed.toLocaleString('vi-VN'), sub: 'Khách có lịch hẹn', icon: Users, change: '+0.0%', up: true, gradient: 'from-[#60a5fa] to-[#93c5fd]' },
          { label: 'Tổng lịch hẹn', value: apptTotal.toLocaleString('vi-VN'), sub: 'Theo kỳ đã chọn', icon: CalendarDays, change: '+0.0%', up: true, gradient: 'from-[#0ea5e9] to-[#38bdf8]' },
        ].map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div key={kpi.label} className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8] hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${kpi.gradient} flex items-center justify-center shadow-md`}>
                  <Icon size={18} className="text-white" />
                </div>
                <span className={`flex items-center gap-0.5 text-xs font-semibold px-2 py-1 rounded-lg ${kpi.up ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'}`}>
                  {kpi.up ? <TrendingUp size={10} /> : <TrendingDown size={10} />} {kpi.change}
                </span>
              </div>
              <div className="text-xl font-bold text-[#0c1e40]">{kpi.value}</div>
              <div className="text-xs font-medium text-[#475569] mt-0.5">{kpi.label}</div>
              <div className="text-xs text-[#94a3b8]">{kpi.sub}</div>
            </div>
          );
        })}
      </div>

      <div className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8]">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-[#0c1e40]">Doanh thu theo tháng</h3>
            <p className="text-[#94a3b8] text-xs mt-0.5">Đơn vị: Triệu đồng</p>
          </div>
          <div className="hidden sm:flex items-center gap-4 text-xs text-[#94a3b8]">
            <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded-sm bg-[#1d4ed8] inline-block" />Doanh thu</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded-sm bg-[#bfdbfe] inline-block" />Chi phí</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded-sm bg-[#6ee7b7] inline-block" />Lợi nhuận</span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={monthlyRevenue} barGap={3} barCategoryGap="25%">
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="revenue" fill="#1d4ed8" radius={[4, 4, 0, 0]} name="Doanh thu" />
            <Bar dataKey="expenses" fill="#bfdbfe" radius={[4, 4, 0, 0]} name="Chi phí" />
            <Bar dataKey="profit" fill="#6ee7b7" radius={[4, 4, 0, 0]} name="Lợi nhuận" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8]">
          <h3 className="text-[#0c1e40] mb-1">Doanh thu theo chi nhánh</h3>
          <p className="text-[#94a3b8] text-xs mb-5">Theo kỳ đã chọn (triệu đồng)</p>
          <div className="space-y-4">
            {branchRevenue.map((b, i) => {
              const max = Math.max(1, ...branchRevenue.map((row) => Number(row.revenue || 0)));
              const pct = (Number(b.revenue || 0) / max) * 100;
              const blues = ['#1d4ed8', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd'];
              return (
                <div key={b.name}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-[#475569]">{b.name}</span>
                    <span className="text-sm font-bold text-[#1d4ed8]">{b.revenue} tr</span>
                  </div>
                  <div className="h-2.5 bg-[#f0f4fb] rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: blues[i % blues.length] }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8]">
          <h3 className="text-[#0c1e40] mb-1">Doanh thu theo dịch vụ</h3>
          <p className="text-[#94a3b8] text-xs mb-2">Phân bổ % theo kỳ</p>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={serviceRevenue} cx="50%" cy="50%" outerRadius={72} dataKey="value" paddingAngle={2}>
                  {serviceRevenue.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: any) => [`${v}%`, '']} contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2eaff' }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-2.5">
              {serviceRevenue.map((item) => (
                <div key={item.name} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm" style={{ background: item.color }} />
                    <span className="text-[#475569]">{item.name}</span>
                  </span>
                  <span className="font-bold text-[#0c1e40]">{item.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8]">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-[#0c1e40]">Lượt khách - Mới vs Quay lại</h3>
            <p className="text-[#94a3b8] text-xs mt-0.5">6 tháng gần đây</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-[#94a3b8]">
            <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 rounded-full bg-[#1d4ed8] inline-block" />Khách mới</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 rounded-full bg-[#bfdbfe] inline-block" />Quay lại</span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={customerGrowth}>
            <defs>
              <linearGradient id="gNew" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1d4ed8" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#1d4ed8" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gRet" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#93c5fd" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#93c5fd" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ borderRadius: 12, fontSize: 12, border: '1px solid #e2eaff' }} formatter={(v: any, name) => [v, name === 'new' ? 'Khách mới' : 'Quay lại']} />
            <Area type="monotone" dataKey="returning" stroke="#93c5fd" strokeWidth={2} fill="url(#gRet)" />
            <Area type="monotone" dataKey="new" stroke="#1d4ed8" strokeWidth={2.5} fill="url(#gNew)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-[#e8eef8] overflow-hidden">
        <div className="px-5 py-4 border-b border-[#e8eef8] bg-[#f8faff]">
          <h3 className="text-[#0c1e40]">Top dịch vụ theo doanh thu</h3>
          <p className="text-[#94a3b8] text-xs mt-0.5">Theo kỳ đã chọn</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[#f8faff] border-b border-[#e8eef8]">
                <th className="text-left px-5 py-3 text-xs font-semibold text-[#64748b] uppercase tracking-wider w-10">#</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[#64748b] uppercase tracking-wider">Dịch vụ</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[#64748b] uppercase tracking-wider hidden md:table-cell">Lượt đặt</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[#64748b] uppercase tracking-wider">Doanh thu</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[#64748b] uppercase tracking-wider hidden md:table-cell">Tăng trưởng</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f4fb]">
              {topServices.map((svc, idx) => (
                <tr key={svc.name} className="hover:bg-[#f8faff] transition-colors">
                  <td className="px-5 py-3.5">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold
                      ${idx === 0 ? 'bg-amber-100 text-amber-700' : idx === 1 ? 'bg-slate-100 text-slate-600' : idx === 2 ? 'bg-orange-100 text-orange-600' : 'bg-blue-50 text-[#3b82f6]'}`}>
                      {idx + 1}
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-sm font-semibold text-[#0c1e40]">{svc.name}</span>
                  </td>
                  <td className="px-5 py-3.5 hidden md:table-cell">
                    <span className="text-sm text-[#475569]">{svc.bookings.toLocaleString('vi-VN')}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-sm font-bold text-[#3b82f6]">{svc.revenue}</span>
                  </td>
                  <td className="px-5 py-3.5 hidden md:table-cell">
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-100 px-2.5 py-1 rounded-lg">
                      <TrendingUp size={10} /> {svc.growth}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
