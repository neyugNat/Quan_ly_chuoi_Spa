import { useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, DollarSign, Users, CalendarDays, Download } from "lucide-react";

const monthlyRevenue = [
  { month: "T1", revenue: 85, expenses: 42, profit: 43 },
  { month: "T2", revenue: 92, expenses: 45, profit: 47 },
  { month: "T3", revenue: 78, expenses: 40, profit: 38 },
  { month: "T4", revenue: 110, expenses: 52, profit: 58 },
  { month: "T5", revenue: 125, expenses: 58, profit: 67 },
  { month: "T6", revenue: 98, expenses: 48, profit: 50 },
  { month: "T7", revenue: 142, expenses: 65, profit: 77 },
  { month: "T8", revenue: 135, expenses: 62, profit: 73 },
  { month: "T9", revenue: 158, expenses: 72, profit: 86 },
  { month: "T10", revenue: 172, expenses: 78, profit: 94 },
  { month: "T11", revenue: 165, expenses: 75, profit: 90 },
  { month: "T12", revenue: 195, expenses: 88, profit: 107 },
];

const branchRevenue = [
  { name: "Quận 1", revenue: 195 },
  { name: "Quận 3", revenue: 162 },
  { name: "Quận 7", revenue: 148 },
  { name: "Thủ Đức", revenue: 125 },
  { name: "Bình Thạnh", revenue: 110 },
];

const serviceRevenue = [
  { name: "Massage", value: 35, color: "#1d4ed8" },
  { name: "Chăm sóc da", value: 28, color: "#4f46e5" },
  { name: "Nail & Tóc", value: 20, color: "#0891b2" },
  { name: "Xông hơi", value: 12, color: "#0369a1" },
  { name: "Gói đặc biệt", value: 5, color: "#1e40af" },
];

const customerGrowth = [
  { month: "T7", new: 45, returning: 120 },
  { month: "T8", new: 52, returning: 130 },
  { month: "T9", new: 61, returning: 148 },
  { month: "T10", new: 78, returning: 162 },
  { month: "T11", new: 69, returning: 170 },
  { month: "T12", new: 124, returning: 185 },
];

const topServices = [
  { name: "Manicure + Pedicure", bookings: 334, revenue: "126,920,000đ", growth: "+18%" },
  { name: "Massage thư giãn 60'", bookings: 312, revenue: "187,200,000đ", growth: "+12%" },
  { name: "Chăm sóc da cơ bản", bookings: 276, revenue: "124,200,000đ", growth: "+9%" },
  { name: "Massage toàn thân 90'", bookings: 248, revenue: "210,800,000đ", growth: "+22%" },
  { name: "Xông hơi thảo dược", bookings: 167, revenue: "58,450,000đ", growth: "+6%" },
];

const periods = ["Tháng này", "Quý này", "6 tháng", "Năm nay"];

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
  const [period, setPeriod] = useState("Năm nay");

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
                className={`px-3 py-2 text-xs font-medium transition-colors ${period === p ? "bg-[#3b82f6] text-white" : "text-[#64748b] hover:bg-[#eff6ff]"}`}
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

      {/* KPIs */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: "Tổng doanh thu", value: "1,555 tr", sub: "Cả 5 chi nhánh", icon: DollarSign, change: "+15.2%", up: true, gradient: "from-[#3b82f6] to-[#60a5fa]" },
          { label: "Tổng lợi nhuận", value: "730 tr", sub: "Biên LN 47%", icon: TrendingUp, change: "+18.5%", up: true, gradient: "from-[#38bdf8] to-[#7dd3fc]" },
          { label: "Khách hàng phục vụ", value: "2,847", sub: "+214 so kỳ trước", icon: Users, change: "+8.2%", up: true, gradient: "from-[#60a5fa] to-[#93c5fd]" },
          { label: "Tổng lịch hẹn", value: "3,124", sub: "Hoàn thành 94%", icon: CalendarDays, change: "+11.3%", up: true, gradient: "from-[#0ea5e9] to-[#38bdf8]" },
        ].map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div key={kpi.label} className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8] hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${kpi.gradient} flex items-center justify-center shadow-md`}>
                  <Icon size={18} className="text-white" />
                </div>
                <span className={`flex items-center gap-0.5 text-xs font-semibold px-2 py-1 rounded-lg ${kpi.up ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-500"}`}>
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

      {/* Revenue bar chart */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8]">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-[#0c1e40]">Doanh thu & Lợi nhuận theo tháng</h3>
            <p className="text-[#94a3b8] text-xs mt-0.5">Đơn vị: Triệu đồng — Năm 2025</p>
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
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="revenue" fill="#1d4ed8" radius={[4, 4, 0, 0]} name="Doanh thu" />
            <Bar dataKey="expenses" fill="#bfdbfe" radius={[4, 4, 0, 0]} name="Chi phí" />
            <Bar dataKey="profit" fill="#6ee7b7" radius={[4, 4, 0, 0]} name="Lợi nhuận" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 2 col */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {/* Branch bars */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8]">
          <h3 className="text-[#0c1e40] mb-1">Doanh thu theo chi nhánh</h3>
          <p className="text-[#94a3b8] text-xs mb-5">Tháng 12/2025 (triệu đồng)</p>
          <div className="space-y-4">
            {branchRevenue.map((b, i) => {
              const pct = (b.revenue / 200) * 100;
              const blues = ["#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"];
              return (
                <div key={b.name}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-[#475569]">{b.name}</span>
                    <span className="text-sm font-bold text-[#1d4ed8]">{b.revenue} tr</span>
                  </div>
                  <div className="h-2.5 bg-[#f0f4fb] rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: blues[i] }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Pie */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8]">
          <h3 className="text-[#0c1e40] mb-1">Doanh thu theo dịch vụ</h3>
          <p className="text-[#94a3b8] text-xs mb-2">Phân bổ % năm 2025</p>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={serviceRevenue} cx="50%" cy="50%" outerRadius={72} dataKey="value" paddingAngle={2}>
                  {serviceRevenue.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: any) => [`${v}%`, ""]} contentStyle={{ fontSize: 11, borderRadius: 8, border: "1px solid #e2eaff" }} />
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

      {/* Customer growth */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8]">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-[#0c1e40]">Lượt khách — Mới vs Quay lại</h3>
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
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ borderRadius: 12, fontSize: 12, border: "1px solid #e2eaff" }} formatter={(v: any, name) => [v, name === "new" ? "Khách mới" : "Quay lại"]} />
            <Area type="monotone" dataKey="returning" stroke="#93c5fd" strokeWidth={2} fill="url(#gRet)" />
            <Area type="monotone" dataKey="new" stroke="#1d4ed8" strokeWidth={2.5} fill="url(#gNew)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Top services table */}
      <div className="bg-white rounded-2xl shadow-sm border border-[#e8eef8] overflow-hidden">
        <div className="px-5 py-4 border-b border-[#e8eef8] bg-[#f8faff]">
          <h3 className="text-[#0c1e40]">Top dịch vụ theo doanh thu</h3>
          <p className="text-[#94a3b8] text-xs mt-0.5">Năm 2025 — Toàn chuỗi</p>
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
                      ${idx === 0 ? "bg-amber-100 text-amber-700" : idx === 1 ? "bg-slate-100 text-slate-600" : idx === 2 ? "bg-orange-100 text-orange-600" : "bg-blue-50 text-[#3b82f6]"}`}>
                      {idx + 1}
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-sm font-semibold text-[#0c1e40]">{svc.name}</span>
                  </td>
                  <td className="px-5 py-3.5 hidden md:table-cell">
                    <span className="text-sm text-[#475569]">{svc.bookings.toLocaleString()}</span>
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