import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../lib/api';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts';
import {
  TrendingUp, CalendarDays, Users, DollarSign, Star,
  Clock, MapPin, ArrowUpRight, ArrowDownRight, CheckCircle2,
  XCircle, AlertCircle, Activity,
} from 'lucide-react';

function formatMoneyVND(value: any) {
  const n = Number(value || 0);
  try {
    return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(n);
  } catch {
    return String(n);
  }
}

function localDateKey(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function toDateOnly(value: any) {
  if (!value) return '';
  const text = String(value);
  if (text.length >= 10) return text.slice(0, 10);
  return '';
}

function formatDateDDMMYYYY(dateValue: Date) {
  const dd = String(dateValue.getDate()).padStart(2, '0');
  const mm = String(dateValue.getMonth() + 1).padStart(2, '0');
  const yyyy = dateValue.getFullYear();
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

function buildTrendFromDaily(items: any[], numericKey: string) {
  const byDay = new Map<string, number>();
  for (const item of items || []) {
    const day = String(item?.day || '').trim();
    if (!day) continue;
    const value = Number(item?.[numericKey] || 0);
    byDay.set(day, (byDay.get(day) || 0) + value);
  }

  const sorted = Array.from(byDay.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  if (sorted.length === 0) return { changeText: '0.0%', up: true };

  const windowSize = Math.max(1, Math.min(7, Math.floor(sorted.length / 2) || 1));
  const current = sorted.slice(-windowSize).reduce((sum, row) => sum + row[1], 0);
  const previous = sorted.slice(-windowSize * 2, -windowSize).reduce((sum, row) => sum + row[1], 0);

  if (previous <= 0) {
    if (current <= 0) return { changeText: '0.0%', up: true };
    return { changeText: '+100.0%', up: true };
  }

  const pct = ((current - previous) / previous) * 100;
  return {
    changeText: `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`,
    up: pct >= 0,
  };
}

const MONTH_LABELS = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'];

const fallbackServiceData = [
  { name: 'Massage', value: 35, color: '#2563eb' },
  { name: 'Chăm sóc da', value: 28, color: '#0ea5e9' },
  { name: 'Nail & Tóc', value: 20, color: '#6366f1' },
  { name: 'Xông hơi', value: 17, color: '#06b6d4' },
];

const branchBarColors = ['#1d4ed8', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd'];

const statusConfig: Record<string, { label: string; icon: any; color: string; bg: string }> = {
  booked: { label: 'Đã đặt', icon: CalendarDays, color: 'text-blue-600', bg: 'bg-blue-50' },
  confirmed: { label: 'Xác nhận', icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
  arrived: { label: 'Đã đến', icon: CheckCircle2, color: 'text-cyan-700', bg: 'bg-cyan-50' },
  in_service: { label: 'Đang làm', icon: Activity, color: 'text-indigo-700', bg: 'bg-indigo-50' },
  completed: { label: 'Hoàn thành', icon: CheckCircle2, color: 'text-emerald-700', bg: 'bg-emerald-50' },
  paid: { label: 'Đã thanh toán', icon: DollarSign, color: 'text-sky-700', bg: 'bg-sky-50' },
  pending: { label: 'Chờ xử lý', icon: AlertCircle, color: 'text-amber-600', bg: 'bg-amber-50' },
  cancelled: { label: 'Đã hủy', icon: XCircle, color: 'text-red-500', bg: 'bg-red-50' },
  no_show: { label: 'Không đến', icon: XCircle, color: 'text-rose-600', bg: 'bg-rose-50' },
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-[#e2eaff] rounded-xl shadow-lg p-3 text-xs">
        <p className="font-semibold text-[#0c1e40] mb-1">{label}</p>
        {payload.map((p: any, i: number) => (
          <p key={i} style={{ color: p.color }}>{p.name}: <b>{p.value} tr</b></p>
        ))}
      </div>
    );
  }
  return null;
};

export function Dashboard() {
  const [revenueItems, setRevenueItems] = useState<any[]>([]);
  const [appointmentItems, setAppointmentItems] = useState<any[]>([]);
  const [lowStockItems, setLowStockItems] = useState<any[]>([]);
  const [customerItems, setCustomerItems] = useState<any[]>([]);
  const [serviceItems, setServiceItems] = useState<any[]>([]);
  const [staffItems, setStaffItems] = useState<any[]>([]);
  const [appointmentList, setAppointmentList] = useState<any[]>([]);
  const [branchItems, setBranchItems] = useState<any[]>([]);
  const [branchPerf, setBranchPerf] = useState<any[]>([]);
  const [yearlyRevenueByMonth, setYearlyRevenueByMonth] = useState<number[]>(new Array(12).fill(0));

  const load = useCallback(async () => {
    try {
      const [revenue, appointmentsReport, lowStock, customers, services, staffs, appointments] = await Promise.all([
        apiFetch('/api/reports/revenue'),
        apiFetch('/api/reports/appointments'),
        apiFetch('/api/reports/low-stock'),
        apiFetch('/api/customers'),
        apiFetch('/api/services'),
        apiFetch('/api/staffs'),
        apiFetch('/api/appointments'),
      ]);

      setRevenueItems(revenue?.items || []);
      setAppointmentItems(appointmentsReport?.items || []);
      setLowStockItems(lowStock?.items || []);
      setCustomerItems(customers?.items || []);
      setServiceItems(services?.items || []);
      setStaffItems(staffs?.items || []);
      setAppointmentList(appointments?.items || []);
    } catch {
      setRevenueItems([]);
      setAppointmentItems([]);
      setLowStockItems([]);
      setCustomerItems([]);
      setServiceItems([]);
      setStaffItems([]);
      setAppointmentList([]);
    }

    try {
      const branches = await apiFetch('/api/branches');
      const branchRows = branches?.items || [];
      setBranchItems(branchRows);

      if (branchRows.length > 0) {
        const totalsByMonth = new Array(12).fill(0);
        const perfRows = await Promise.all(
          branchRows.slice(0, 5).map(async (branch: any) => {
            try {
              const headers = { 'X-Branch-Id': String(branch.id) };
              const [rev, apt] = await Promise.all([
                apiFetch('/api/reports/revenue', { headers }),
                apiFetch('/api/reports/appointments', { headers }),
              ]);

              (rev?.items || []).forEach((it: any) => {
                const day = String(it?.day || '');
                const month = Number(day.slice(5, 7));
                if (month >= 1 && month <= 12) {
                  totalsByMonth[month - 1] += Number(it?.revenue || 0);
                }
              });

              const revenueTotalByBranch = (rev?.items || []).reduce((sum: number, it: any) => sum + Number(it?.revenue || 0), 0);
              const appointmentTotalByBranch = (apt?.items || []).reduce((sum: number, it: any) => sum + Number(it?.total || 0), 0);

              return {
                branch: branch?.name || `CN #${branch?.id}`,
                revenue: Math.round(revenueTotalByBranch / 1000000),
                appointments: appointmentTotalByBranch,
              };
            } catch {
              return null;
            }
          }),
        );

        const resolved = perfRows.filter(Boolean).sort((a: any, b: any) => Number(b?.revenue || 0) - Number(a?.revenue || 0));
        setBranchPerf(resolved);
        setYearlyRevenueByMonth(totalsByMonth);
      } else {
        setBranchPerf([]);
        setYearlyRevenueByMonth(new Array(12).fill(0));
      }
    } catch {
      setBranchItems([]);
      setBranchPerf([]);
      setYearlyRevenueByMonth(new Array(12).fill(0));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const customerNameById = useMemo(() => {
    const map = new Map<number, string>();
    customerItems.forEach((item: any) => {
      map.set(Number(item?.id), item?.full_name || `KH #${item?.id}`);
    });
    return map;
  }, [customerItems]);

  const serviceNameById = useMemo(() => {
    const map = new Map<number, string>();
    serviceItems.forEach((item: any) => {
      map.set(Number(item?.id), item?.name || `DV #${item?.id}`);
    });
    return map;
  }, [serviceItems]);

  const branchNameById = useMemo(() => {
    const map = new Map<number, string>();
    branchItems.forEach((item: any) => {
      map.set(Number(item?.id), item?.name || `CN #${item?.id}`);
    });
    return map;
  }, [branchItems]);

  const revenueTotal = useMemo(() => revenueItems.reduce((sum, it) => sum + Number(it?.revenue || 0), 0), [revenueItems]);
  const apptTotal = useMemo(() => appointmentItems.reduce((sum, it) => sum + Number(it?.total || 0), 0), [appointmentItems]);
  const apptCancelled = useMemo(() => appointmentItems.reduce((sum, it) => sum + Number(it?.cancelled || 0), 0), [appointmentItems]);
  const paymentsTotal = useMemo(() => revenueItems.reduce((sum, it) => sum + Number(it?.payments_count || 0), 0), [revenueItems]);
  const lowStockCount = useMemo(() => lowStockItems.length, [lowStockItems]);

  const revenueTrend = useMemo(() => buildTrendFromDaily(revenueItems, 'revenue'), [revenueItems]);
  const appointmentTrend = useMemo(() => buildTrendFromDaily(appointmentItems, 'total'), [appointmentItems]);
  const paymentTrend = useMemo(() => buildTrendFromDaily(revenueItems, 'payments_count'), [revenueItems]);

  const dynamicStats = [
    {
      label: 'Doanh thu',
      value: `${formatMoneyVND(revenueTotal)}đ`,
      change: revenueTrend.changeText,
      up: revenueTrend.up,
      icon: DollarSign,
      gradient: 'from-[#3b82f6] to-[#60a5fa]',
      light: 'bg-blue-50',
      iconColor: 'text-blue-600',
    },
    {
      label: 'Lịch hẹn',
      value: `${apptTotal}`,
      change: appointmentTrend.changeText,
      up: appointmentTrend.up,
      icon: CalendarDays,
      gradient: 'from-[#38bdf8] to-[#7dd3fc]',
      light: 'bg-sky-50',
      iconColor: 'text-sky-600',
    },
    {
      label: 'Giao dịch',
      value: `${paymentsTotal}`,
      change: paymentTrend.changeText,
      up: paymentTrend.up,
      icon: Users,
      gradient: 'from-[#60a5fa] to-[#93c5fd]',
      light: 'bg-blue-50',
      iconColor: 'text-blue-500',
    },
    {
      label: 'Hàng sắp hết',
      value: `${lowStockCount}`,
      change: lowStockCount === 0 ? 'Ổn định' : `${lowStockCount} cảnh báo`,
      up: lowStockCount === 0,
      icon: AlertCircle,
      gradient: 'from-[#38bdf8] to-[#60a5fa]',
      light: 'bg-sky-50',
      iconColor: 'text-sky-500',
    },
  ];

  const dynamicRevenueData = useMemo(() => {
    const totals = [...yearlyRevenueByMonth];
    const totalAllBranches = totals.reduce((sum, value) => sum + Number(value || 0), 0);

    if (totalAllBranches <= 0) {
      revenueItems.forEach((it: any) => {
        const day = String(it?.day || '');
        const month = Number(day.slice(5, 7));
        if (month >= 1 && month <= 12) {
          totals[month - 1] += Number(it?.revenue || 0);
        }
      });
    }

    return MONTH_LABELS.map((month, idx) => {
      const revenue = Math.max(0, Math.round(Number(totals[idx] || 0) / 1000000));
      return {
        month,
        revenue,
        target: Math.max(0, Math.round(revenue * 1.08)),
      };
    });
  }, [yearlyRevenueByMonth, revenueItems]);

  const dynamicServiceData = useMemo(() => {
    const palette = ['#2563eb', '#0ea5e9', '#6366f1', '#06b6d4', '#3b82f6'];

    const revenueByService = new Map<number, number>();
    revenueItems.forEach((it: any) => {
      const serviceId = Number(it?.service_id || 0);
      if (!serviceId) return;
      revenueByService.set(serviceId, (revenueByService.get(serviceId) || 0) + Number(it?.revenue || 0));
    });

    if (revenueByService.size > 0) {
      const rows = Array.from(revenueByService.entries())
        .map(([serviceId, amount]) => ({
          serviceId,
          name: serviceNameById.get(serviceId) || `Dịch vụ #${serviceId}`,
          raw: amount,
        }))
        .sort((a, b) => b.raw - a.raw)
        .slice(0, 5);

      const total = rows.reduce((sum, row) => sum + row.raw, 0);
      if (total > 0) {
        return rows
          .map((row, idx) => ({
            name: row.name,
            value: Math.max(1, Math.round((row.raw / total) * 100)),
            color: palette[idx % palette.length],
          }))
          .slice(0, 4);
      }
    }

    const countByService = new Map<number, number>();
    appointmentList.forEach((it: any) => {
      const serviceId = Number(it?.service_id || 0);
      if (!serviceId) return;
      countByService.set(serviceId, (countByService.get(serviceId) || 0) + 1);
    });

    if (countByService.size > 0) {
      const rows = Array.from(countByService.entries())
        .map(([serviceId, total]) => ({
          serviceId,
          name: serviceNameById.get(serviceId) || `Dịch vụ #${serviceId}`,
          raw: total,
        }))
        .sort((a, b) => b.raw - a.raw)
        .slice(0, 5);
      const total = rows.reduce((sum, row) => sum + row.raw, 0);
      return rows
        .map((row, idx) => ({
          name: row.name,
          value: Math.max(1, Math.round((row.raw / total) * 100)),
          color: palette[idx % palette.length],
        }))
        .slice(0, 4);
    }

    return fallbackServiceData;
  }, [revenueItems, appointmentList, serviceNameById]);

  const dynamicBranchData = useMemo(() => {
    if (branchPerf.length > 0) return branchPerf;
    const fallbackName = branchItems[0]?.name || 'Chi nhánh hiện tại';
    return [{ branch: fallbackName, revenue: Math.round(revenueTotal / 1000000), appointments: apptTotal }];
  }, [branchPerf, branchItems, revenueTotal, apptTotal]);

  const todayKey = useMemo(() => localDateKey(new Date()), []);
  const todayLabel = useMemo(() => formatDateDDMMYYYY(new Date()), []);

  const todayAppointments = useMemo(() => {
    return appointmentList
      .filter((item: any) => toDateOnly(item?.start_time) === todayKey)
      .sort((a: any, b: any) => new Date(a?.start_time || 0).getTime() - new Date(b?.start_time || 0).getTime())
      .slice(0, 5)
      .map((item: any) => ({
        id: item?.id,
        customer: customerNameById.get(Number(item?.customer_id)) || `Khách #${item?.customer_id || ''}`,
        service: serviceNameById.get(Number(item?.service_id)) || 'Chưa gán dịch vụ',
        time: formatTimeHHMM(item?.start_time),
        branch: branchNameById.get(Number(item?.branch_id)) || `CN #${item?.branch_id || ''}`,
        status: String(item?.status || 'booked'),
      }));
  }, [appointmentList, todayKey, customerNameById, serviceNameById, branchNameById]);

  const todayReportCount = useMemo(() => {
    const row = appointmentItems.find((item: any) => item?.day === todayKey);
    if (row) return Number(row?.total || 0);
    return todayAppointments.length;
  }, [appointmentItems, todayKey, todayAppointments.length]);

  const activeStaffCount = useMemo(() => {
    return staffItems.filter((item: any) => String(item?.status || 'active') === 'active').length;
  }, [staffItems]);

  const activeServiceCount = useMemo(() => {
    return serviceItems.filter((item: any) => String(item?.status || 'active') === 'active').length;
  }, [serviceItems]);

  const cancelRate = useMemo(() => {
    if (!apptTotal) return '0.0%';
    return `${((apptCancelled / apptTotal) * 100).toFixed(1)}%`;
  }, [apptCancelled, apptTotal]);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {dynamicStats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-[#e8eef8] dark:border-gray-700 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center shadow-md`}>
                  <Icon size={20} className="text-white" />
                </div>
                <span className={`flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-lg ${stat.up ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'}`}>
                  {stat.up ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                  {stat.change}
                </span>
              </div>
              <div className="text-[#0c1e40] dark:text-gray-100 text-2xl font-bold">{stat.value}</div>
              <div className="text-[#94a3b8] dark:text-gray-400 text-xs mt-1">{stat.label}</div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="xl:col-span-2 bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-[#e8eef8] dark:border-gray-700">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-[#0c1e40] dark:text-gray-100">Doanh thu theo năm (12 tháng)</h3>
              <p className="text-[#94a3b8] dark:text-gray-400 text-xs mt-0.5">Đơn vị: Triệu đồng • Tổng các chi nhánh (tạm fake)</p>
            </div>
            <div className="flex items-center gap-4 text-xs text-[#94a3b8] dark:text-gray-400">
              <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 rounded-full bg-[#1d4ed8] inline-block" />Thực tế</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 rounded-full bg-[#bfdbfe] inline-block" />Mục tiêu</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={dynamicRevenueData}>
              <defs>
                <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1d4ed8" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#1d4ed8" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorTgt" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#93c5fd" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#93c5fd" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="target" stroke="#bfdbfe" strokeWidth={2} strokeDasharray="5 5" fill="url(#colorTgt)" name="Mục tiêu" />
              <Area type="monotone" dataKey="revenue" stroke="#1d4ed8" strokeWidth={2.5} fill="url(#colorRev)" name="Thực tế" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-[#e8eef8] dark:border-gray-700">
          <h3 className="text-[#0c1e40] dark:text-gray-100 mb-1">Phân bổ dịch vụ</h3>
          <p className="text-[#94a3b8] dark:text-gray-400 text-xs mb-3">Theo dữ liệu backend</p>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={dynamicServiceData} cx="50%" cy="50%" innerRadius={42} outerRadius={72} paddingAngle={3} dataKey="value">
                {dynamicServiceData.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: any) => [`${value}%`, '']} contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid #e2eaff' }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-2">
            {dynamicServiceData.map((item) => (
              <div key={item.name} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-2 text-[#475569] dark:text-gray-400">
                  <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: item.color }} />
                  {item.name}
                </span>
                <span className="font-semibold text-[#0c1e40] dark:text-gray-200">{item.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-[#e8eef8] dark:border-gray-700">
          <h3 className="text-[#0c1e40] dark:text-gray-100 mb-1">Hiệu suất chi nhánh</h3>
          <p className="text-[#94a3b8] dark:text-gray-400 text-xs mb-4">Doanh thu (triệu đồng)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={dynamicBranchData} layout="vertical" barSize={9}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="branch" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} width={92} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid #e2eaff' }} formatter={(v: any) => [`${v} tr`, 'Doanh thu']} />
              <Bar dataKey="revenue" radius={[0, 6, 6, 0]}>
                {dynamicBranchData.map((_: any, i: number) => (
                  <Cell key={i} fill={branchBarColors[i % branchBarColors.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="xl:col-span-2 bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-[#e8eef8] dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-[#0c1e40] dark:text-gray-100">Lịch hẹn hôm nay</h3>
              <p className="text-[#94a3b8] dark:text-gray-400 text-xs mt-0.5">{todayLabel} • {todayReportCount} lịch hẹn</p>
            </div>
            <button className="text-xs text-[#1d4ed8] font-semibold bg-blue-50 dark:bg-blue-900/30 px-3 py-1.5 rounded-lg hover:bg-blue-100 transition-colors">Xem tất cả</button>
          </div>
          <div className="space-y-2">
            {todayAppointments.length > 0 ? todayAppointments.map((apt) => {
              const s = statusConfig[apt.status] || statusConfig.booked;
              const SIcon = s.icon;
              return (
                <div key={apt.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-[#f8faff] dark:hover:bg-gray-700/50 transition-colors border border-transparent hover:border-[#e2eaff] dark:hover:border-gray-600">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#3b82f6] to-[#1d4ed8] flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                    {String(apt.customer || '?').charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-[#0c1e40] dark:text-gray-100 truncate">{apt.customer}</div>
                    <div className="text-xs text-[#94a3b8] dark:text-gray-400 truncate">{apt.service}</div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="flex items-center gap-1 text-xs text-[#3b82f6]"><Clock size={10} />{apt.time}</span>
                      <span className="flex items-center gap-1 text-xs text-[#94a3b8] dark:text-gray-400"><MapPin size={10} />{apt.branch}</span>
                    </div>
                  </div>
                  <span className={`flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full ${s.bg} ${s.color} flex-shrink-0`}>
                    <SIcon size={10} /><span className="hidden sm:inline">{s.label}</span>
                  </span>
                </div>
              );
            }) : (
              <div className="text-xs text-[#94a3b8] py-6 text-center border border-dashed border-[#dbeafe] rounded-xl">
                Chưa có lịch hẹn nào trong hôm nay.
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Tổng chi nhánh', value: `${branchItems.length || 1}`, sub: branchItems.length ? 'Đang hoạt động' : 'Theo chi nhánh hiện tại', icon: MapPin, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/30' },
          { label: 'Nhân viên', value: `${staffItems.length}`, sub: `${activeStaffCount} đang hoạt động`, icon: Users, color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-900/30' },
          { label: 'Dịch vụ', value: `${serviceItems.length}`, sub: `${activeServiceCount} đang hoạt động`, icon: TrendingUp, color: 'text-cyan-600', bg: 'bg-cyan-50 dark:bg-cyan-900/30' },
          { label: 'Tỉ lệ hủy', value: cancelRate, sub: `${apptCancelled}/${apptTotal} lịch`, icon: Activity, color: 'text-sky-600', bg: 'bg-sky-50 dark:bg-sky-900/30' },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm border border-[#e8eef8] dark:border-gray-700 flex items-center gap-3 hover:shadow-md transition-shadow">
              <div className={`w-10 h-10 rounded-xl ${item.bg} flex items-center justify-center flex-shrink-0`}>
                <Icon size={18} className={item.color} />
              </div>
              <div>
                <div className="text-xl font-bold text-[#0c1e40] dark:text-gray-100">{item.value}</div>
                <div className="text-xs text-[#475569] dark:text-gray-300 font-medium leading-tight">{item.label}</div>
                <div className="text-xs text-[#94a3b8] dark:text-gray-400">{item.sub}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
