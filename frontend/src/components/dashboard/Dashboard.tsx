import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../lib/api';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar,
} from "recharts";
import {
  TrendingUp, CalendarDays, Users, DollarSign, Star,
  Clock, MapPin, ArrowUpRight, ArrowDownRight, CheckCircle2,
  XCircle, AlertCircle, Activity,
} from "lucide-react";

function formatMoneyVND(value: any) {
  const n = Number(value || 0);
  try {
    return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(n);
  } catch { return String(n); }
}

const fallbackRevenueData = [
  { month: "T1", revenue: 85, target: 90 },
  { month: "T2", revenue: 92, target: 90 },
  { month: "T3", revenue: 78, target: 90 },
  { month: "T4", revenue: 110, target: 95 },
  { month: "T5", revenue: 125, target: 100 },
  { month: "T6", revenue: 98, target: 100 },
  { month: "T7", revenue: 142, target: 110 },
  { month: "T8", revenue: 135, target: 110 },
  { month: "T9", revenue: 158, target: 120 },
  { month: "T10", revenue: 172, target: 130 },
  { month: "T11", revenue: 165, target: 140 },
  { month: "T12", revenue: 195, target: 150 },
];

const serviceData = [
  { name: "Massage", value: 35, color: "#2563eb" },
  { name: "Chăm sóc da", value: 28, color: "#0ea5e9" },
  { name: "Nail & Tóc", value: 20, color: "#6366f1" },
  { name: "Xông hơi", value: 17, color: "#06b6d4" },
];

const branchData = [
  { branch: "Quận 1", revenue: 195, appointments: 148 },
  { branch: "Quận 3", revenue: 162, appointments: 122 },
  { branch: "Quận 7", revenue: 148, appointments: 108 },
  { branch: "Thủ Đức", revenue: 125, appointments: 92 },
  { branch: "Bình Thạnh", revenue: 110, appointments: 85 },
];

const upcomingAppointments = [
  { id: 1, customer: "Nguyễn Thị Hoa", service: "Massage toàn thân 90 phút", time: "09:00", branch: "Quận 1", status: "confirmed" },
  { id: 2, customer: "Lê Thị Thu", service: "Chăm sóc da cơ bản", time: "10:30", branch: "Quận 3", status: "confirmed" },
  { id: 3, customer: "Phạm Văn Nam", service: "Xông hơi thảo dược", time: "11:00", branch: "Quận 7", status: "pending" },
  { id: 4, customer: "Trần Thị Bình", service: "Manicure + Pedicure", time: "13:30", branch: "Quận 1", status: "confirmed" },
  { id: 5, customer: "Hoàng Văn Minh", service: "Massage đá nóng", time: "14:00", branch: "Bình Thạnh", status: "cancelled" },
];

const stats = [
  { label: "Doanh thu tháng", value: "195,4 tr", change: "+12.5%", up: true, icon: DollarSign, gradient: "from-[#3b82f6] to-[#60a5fa]", light: "bg-blue-50", iconColor: "text-blue-600" },
  { label: "Lịch hẹn hôm nay", value: "48", change: "+8.2%", up: true, icon: CalendarDays, gradient: "from-[#38bdf8] to-[#7dd3fc]", light: "bg-sky-50", iconColor: "text-sky-600" },
  { label: "Khách hàng mới", value: "124", change: "+15.3%", up: true, icon: Users, gradient: "from-[#60a5fa] to-[#93c5fd]", light: "bg-blue-50", iconColor: "text-blue-500" },
  { label: "Đánh giá trung bình", value: "4.8", change: "-0.1", up: false, icon: Star, gradient: "from-[#38bdf8] to-[#60a5fa]", light: "bg-sky-50", iconColor: "text-sky-500" },
];

const statusConfig: Record<string, { label: string; icon: any; color: string; bg: string }> = {
  confirmed: { label: "Xác nhận", icon: CheckCircle2, color: "text-emerald-600", bg: "bg-emerald-50" },
  pending: { label: "Chờ xử lý", icon: AlertCircle, color: "text-amber-600", bg: "bg-amber-50" },
  cancelled: { label: "Đã hủy", icon: XCircle, color: "text-red-500", bg: "bg-red-50" },
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

  const load = useCallback(async () => {
    try {
      const [revenue, appointments, lowStock] = await Promise.all([
        apiFetch(`/api/reports/revenue`),
        apiFetch(`/api/reports/appointments`),
        apiFetch('/api/reports/low-stock'),
      ]);
      setRevenueItems(revenue?.items || []);
      setAppointmentItems(appointments?.items || []);
      setLowStockItems(lowStock?.items || []);
    } catch {}
  }, []);

  useEffect(() => { load(); }, [load]);

  const revenueTotal = useMemo(() => revenueItems.reduce((sum, it) => sum + Number(it?.revenue || 0), 0), [revenueItems]);
  const apptTotal = useMemo(() => appointmentItems.reduce((sum, it) => sum + Number(it?.total || 0), 0), [appointmentItems]);
  const paymentsTotal = useMemo(() => revenueItems.reduce((sum, it) => sum + Number(it?.payments_count || 0), 0), [revenueItems]);
  const lowStockCount = useMemo(() => lowStockItems.length, [lowStockItems]);

  const dynamicStats = [
    { label: "Doanh thu", value: `${formatMoneyVND(revenueTotal)}đ`, change: "+12.5%", up: true, icon: DollarSign, gradient: "from-[#3b82f6] to-[#60a5fa]", light: "bg-blue-50", iconColor: "text-blue-600" },
    { label: "Lịch hẹn", value: `${apptTotal}`, change: "+8.2%", up: true, icon: CalendarDays, gradient: "from-[#38bdf8] to-[#7dd3fc]", light: "bg-sky-50", iconColor: "text-sky-600" },
    { label: "Giao dịch", value: `${paymentsTotal}`, change: "+15.3%", up: true, icon: Users, gradient: "from-[#60a5fa] to-[#93c5fd]", light: "bg-blue-50", iconColor: "text-blue-500" },
    { label: "Hàng sắp hết", value: `${lowStockCount}`, change: "-1.2%", up: false, icon: AlertCircle, gradient: "from-[#38bdf8] to-[#60a5fa]", light: "bg-sky-50", iconColor: "text-sky-500" },
  ];

  const dynamicRevenueData = useMemo(() => {
    if (revenueItems.length === 0) return fallbackRevenueData;
    return revenueItems.map(it => ({
      month: it.day,
      revenue: Math.round(Number(it.revenue) / 1000000), 
      target: Math.round((Number(it.revenue) / 1000000) * 1.1) 
    }));
  }, [revenueItems]);

  return (
    <div className="space-y-5">
      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {dynamicStats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-[#e8eef8] dark:border-gray-700 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center shadow-md`}>
                  <Icon size={20} className="text-white" />
                </div>
                <span className={`flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-lg ${stat.up ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-500"}`}>
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

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Revenue chart */}
        <div className="xl:col-span-2 bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-[#e8eef8] dark:border-gray-700">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-[#0c1e40] dark:text-gray-100">Doanh thu năm 2025</h3>
              <p className="text-[#94a3b8] dark:text-gray-400 text-xs mt-0.5">Đơn vị: Triệu đồng</p>
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
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="target" stroke="#bfdbfe" strokeWidth={2} strokeDasharray="5 5" fill="url(#colorTgt)" name="Mục tiêu" />
              <Area type="monotone" dataKey="revenue" stroke="#1d4ed8" strokeWidth={2.5} fill="url(#colorRev)" name="Thực tế" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Service breakdown */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-[#e8eef8] dark:border-gray-700">
          <h3 className="text-[#0c1e40] dark:text-gray-100 mb-1">Phân bổ dịch vụ</h3>
          <p className="text-[#94a3b8] dark:text-gray-400 text-xs mb-3">Tháng này</p>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={serviceData} cx="50%" cy="50%" innerRadius={42} outerRadius={72} paddingAngle={3} dataKey="value">
                {serviceData.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: any) => [`${value}%`, ""]} contentStyle={{ fontSize: 12, borderRadius: 10, border: "1px solid #e2eaff" }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-2">
            {serviceData.map((item) => (
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

      {/* Branch + Appointments */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Branch bar chart */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-[#e8eef8] dark:border-gray-700">
          <h3 className="text-[#0c1e40] dark:text-gray-100 mb-1">Hiệu suất chi nhánh</h3>
          <p className="text-[#94a3b8] dark:text-gray-400 text-xs mb-4">Doanh thu (triệu đồng)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={branchData} layout="vertical" barSize={9}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="branch" tick={{ fontSize: 11, fill: "#475569" }} axisLine={false} tickLine={false} width={62} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 10, border: "1px solid #e2eaff" }} formatter={(v: any) => [`${v} tr`, "Doanh thu"]} />
              <Bar dataKey="revenue" radius={[0, 6, 6, 0]}>
                {branchData.map((_, i) => (
                  <Cell key={i} fill={["#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"][i]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Upcoming */}
        <div className="xl:col-span-2 bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-[#e8eef8] dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-[#0c1e40] dark:text-gray-100">Lịch hẹn hôm nay</h3>
              <p className="text-[#94a3b8] dark:text-gray-400 text-xs mt-0.5">24/03/2026 • 48 lịch hẹn</p>
            </div>
            <button className="text-xs text-[#1d4ed8] font-semibold bg-blue-50 dark:bg-blue-900/30 px-3 py-1.5 rounded-lg hover:bg-blue-100 transition-colors">Xem tất cả</button>
          </div>
          <div className="space-y-2">
            {upcomingAppointments.map((apt) => {
              const s = statusConfig[apt.status];
              const SIcon = s.icon;
              return (
                <div key={apt.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-[#f8faff] dark:hover:bg-gray-700/50 transition-colors border border-transparent hover:border-[#e2eaff] dark:hover:border-gray-600">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#3b82f6] to-[#1d4ed8] flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                    {apt.customer.charAt(0)}
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
            })}
          </div>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Tổng chi nhánh", value: "5", sub: "Đang hoạt động", icon: MapPin, color: "text-blue-600", bg: "bg-blue-50 dark:bg-blue-900/30" },
          { label: "Nhân viên", value: "87", sub: "18 part-time", icon: Users, color: "text-indigo-600", bg: "bg-indigo-50 dark:bg-indigo-900/30" },
          { label: "Dịch vụ", value: "42", sub: "6 mới tháng này", icon: TrendingUp, color: "text-cyan-600", bg: "bg-cyan-50 dark:bg-cyan-900/30" },
          { label: "Tỉ lệ hủy", value: "4.2%", sub: "Giảm 0.8%", icon: Activity, color: "text-sky-600", bg: "bg-sky-50 dark:bg-sky-900/30" },
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