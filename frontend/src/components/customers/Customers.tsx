import { useState } from "react";
import { Search, Plus, Star, Phone, Mail, Calendar, Crown, Gift, XCircle, ChevronLeft, ChevronRight, TrendingUp } from "lucide-react";

const customers = [
  { id: 1, name: "Nguyễn Thị Hoa", phone: "0901234567", email: "hoa.nguyen@gmail.com", joined: "15/01/2024", visits: 24, totalSpent: "18,500,000đ", lastVisit: "20/03/2026", tier: "vip", rating: 5 },
  { id: 2, name: "Lê Thị Thu", phone: "0912345678", email: "thu.le@gmail.com", joined: "03/03/2024", visits: 18, totalSpent: "12,300,000đ", lastVisit: "18/03/2026", tier: "gold", rating: 5 },
  { id: 3, name: "Phạm Văn Nam", phone: "0923456789", email: "nam.pham@gmail.com", joined: "20/06/2024", visits: 12, totalSpent: "7,800,000đ", lastVisit: "15/03/2026", tier: "silver", rating: 4 },
  { id: 4, name: "Trần Thị Bình", phone: "0934567890", email: "binh.tran@gmail.com", joined: "10/08/2024", visits: 8, totalSpent: "4,200,000đ", lastVisit: "22/03/2026", tier: "silver", rating: 4 },
  { id: 5, name: "Hoàng Văn Minh", phone: "0945678901", email: "minh.hoang@gmail.com", joined: "05/09/2024", visits: 5, totalSpent: "2,850,000đ", lastVisit: "10/03/2026", tier: "member", rating: 3 },
  { id: 6, name: "Võ Thị Hương", phone: "0956789012", email: "huong.vo@gmail.com", joined: "12/02/2024", visits: 31, totalSpent: "28,900,000đ", lastVisit: "23/03/2026", tier: "vip", rating: 5 },
  { id: 7, name: "Đặng Văn Tú", phone: "0967890123", email: "tu.dang@gmail.com", joined: "28/04/2024", visits: 15, totalSpent: "9,600,000đ", lastVisit: "19/03/2026", tier: "gold", rating: 4 },
  { id: 8, name: "Bùi Thị Lan", phone: "0978901234", email: "lan.bui@gmail.com", joined: "14/07/2024", visits: 9, totalSpent: "5,400,000đ", lastVisit: "21/03/2026", tier: "silver", rating: 4 },
  { id: 9, name: "Ngô Văn Hải", phone: "0989012345", email: "hai.ngo@gmail.com", joined: "01/11/2024", visits: 3, totalSpent: "1,200,000đ", lastVisit: "05/03/2026", tier: "member", rating: 3 },
  { id: 10, name: "Lý Thị Mỹ", phone: "0990123456", email: "my.ly@gmail.com", joined: "22/01/2025", visits: 6, totalSpent: "3,780,000đ", lastVisit: "17/03/2026", tier: "silver", rating: 4 },
];

const tierConfig: Record<string, { label: string; color: string; bg: string; border: string; icon: any }> = {
  vip: {
    label: "VIP",
    color: "text-red-700 dark:text-red-50",
    bg: "bg-red-50 dark:bg-red-400/30",
    border: "border-red-200 dark:border-red-300/70",
    icon: Crown,
  },
  gold: {
    label: "Vàng",
    color: "text-[#a16207] dark:text-[#fcd34d]",
    bg: "bg-[#fff8db] dark:bg-[#a16207]/25",
    border: "border-[#f6d365] dark:border-[#f6d365]/50",
    icon: Star,
  },
  silver: {
    label: "Bạc",
    color: "text-[#334155] dark:text-[#f8fafc]",
    bg: "bg-gradient-to-r from-[#eef2f7] to-[#ffffff] dark:from-[#cbd5e1]/28 dark:to-[#f1f5f9]/18",
    border: "border-[#cbd5e1] dark:border-[#cbd5e1]/60",
    icon: Gift,
  },
  member: {
    label: "Thành viên",
    color: "text-[#7c4b2a] dark:text-[#d3b59b]",
    bg: "bg-[#f6eee8] dark:bg-[#3b2a1d]/72",
    border: "border-[#d2b49c] dark:border-[#6f5038]",
    icon: Gift,
  },
};

const avatarGradients = [
  "from-[#3b82f6] to-[#60a5fa]",
  "from-[#38bdf8] to-[#7dd3fc]",
  "from-[#60a5fa] to-[#93c5fd]",
  "from-[#0ea5e9] to-[#38bdf8]",
  "from-[#3b82f6] to-[#93c5fd]",
];

export function Customers() {
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("Tất cả");
  const [showModal, setShowModal] = useState(false);
  const tierFilters = ["Tất cả", "VIP", "Vàng", "Bạc", "Thành viên"];

  const filtered = customers.filter((c) => {
    const matchSearch = c.name.toLowerCase().includes(search.toLowerCase()) || c.phone.includes(search);
    const matchTier = tierFilter === "Tất cả" || tierConfig[c.tier]?.label === tierFilter;
    return matchSearch && matchTier;
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-[#64748b] text-sm">Quản lý hồ sơ và hành trình khách hàng</p>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white px-4 py-2.5 rounded-xl hover:opacity-90 text-sm font-medium shadow-md shadow-blue-200"
        >
          <Plus size={16} /> Thêm khách hàng
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Tổng khách hàng", value: customers.length, color: "text-[#3b82f6]", bg: "bg-blue-50", border: "border-blue-100" },
          { label: "Khách VIP", value: customers.filter(c => c.tier === "vip").length, color: "text-red-700", bg: "bg-red-50", border: "border-red-100" },
          { label: "Khách Vàng", value: customers.filter(c => c.tier === "gold").length, color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-100" },
          { label: "Khách mới tháng", value: 12, color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-100" },
        ].map((item) => (
          <div key={item.label} className={`${item.bg} border ${item.border} rounded-xl p-4`}>
            <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
            <div className="text-xs text-[#64748b] font-medium mt-0.5">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Search & filter */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#dbeafe]">
        <div className="flex items-center gap-2 bg-[#eff6ff] border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 mb-3">
          <Search size={15} className="text-[#93c5fd] flex-shrink-0" />
          <input
            type="text"
            placeholder="Tìm tên, số điện thoại..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent text-sm text-[#1e3a8a] placeholder-[#93c5fd] outline-none w-full"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {tierFilters.map((f) => (
            <button
              key={f}
              onClick={() => setTierFilter(f)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${tierFilter === f ? "bg-[#3b82f6] text-white shadow-sm" : "bg-[#eff6ff] text-[#475569] hover:bg-[#dbeafe] hover:text-[#3b82f6]"}`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Customer cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((customer, idx) => {
          const tier = tierConfig[customer.tier];
          const TierIcon = tier.icon;
          return (
            <div key={customer.id} className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8] hover:shadow-md hover:border-[#bfdbfe] transition-all">
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${avatarGradients[idx % avatarGradients.length]} flex items-center justify-center text-white font-bold text-base shadow-md`}>
                    {customer.name.charAt(0)}
                  </div>
                  <div>
                    <div className="font-semibold text-[#0c1e40] text-sm">{customer.name}</div>
                    <div className="flex items-center gap-1 text-xs text-[#94a3b8] mt-0.5">
                      <Phone size={10} /> {customer.phone}
                    </div>
                  </div>
                </div>
                <span className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border ${tier.bg} ${tier.color} ${tier.border}`}>
                  <TierIcon size={10} /> {tier.label}
                </span>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-2 mb-4 bg-[#f8faff] rounded-xl p-3">
                <div className="text-center">
                  <div className="text-sm font-bold text-[#0c1e40]">{customer.visits}</div>
                  <div className="text-xs text-[#94a3b8]">Lượt visit</div>
                </div>
                <div className="text-center border-x border-[#e8eef8]">
                  <div className="text-xs font-bold text-[#1d4ed8] truncate px-1">{customer.totalSpent.replace("đ", "")}</div>
                  <div className="text-xs text-[#94a3b8]">Tổng chi</div>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-0.5">
                    {Array(customer.rating).fill(0).map((_, i) => (
                      <Star key={i} size={10} className="text-amber-400 fill-amber-400" />
                    ))}
                  </div>
                  <div className="text-xs text-[#94a3b8] mt-0.5">Đánh giá</div>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-[#94a3b8] mb-4">
                <span className="flex items-center gap-1"><Calendar size={10} className="text-[#3b82f6]" /> Từ {customer.joined}</span>
                <span>Gần nhất: {customer.lastVisit}</span>
              </div>

              <div className="flex items-center gap-2">
                <button className="flex-1 py-2 border border-[#bfdbfe] rounded-xl text-xs font-semibold text-[#475569] hover:bg-[#eff6ff] transition-colors">Lịch sử</button>
                <button className="flex-1 py-2 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white rounded-xl text-xs font-semibold hover:opacity-90 shadow-sm shadow-blue-200">Đặt lịch</button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-[#94a3b8]">Hiển thị <span className="font-semibold text-[#475569]">{filtered.length}</span> / {customers.length} khách hàng</span>
        <div className="flex items-center gap-1">
          <button className="w-8 h-8 rounded-lg border border-[#bfdbfe] flex items-center justify-center text-[#94a3b8] hover:bg-[#dbeafe] hover:text-[#3b82f6] transition-colors"><ChevronLeft size={14} /></button>
          <button className="w-8 h-8 rounded-lg bg-[#3b82f6] text-white text-xs font-semibold">1</button>
          <button className="w-8 h-8 rounded-lg border border-[#bfdbfe] text-xs text-[#475569] hover:bg-[#dbeafe] hover:text-[#3b82f6] transition-colors">2</button>
          <button className="w-8 h-8 rounded-lg border border-[#bfdbfe] flex items-center justify-center text-[#94a3b8] hover:bg-[#dbeafe] hover:text-[#3b82f6] transition-colors"><ChevronRight size={14} /></button>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-[#dbeafe]">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-[#1e3a8a]">Thêm khách hàng mới</h3>
                <p className="text-[#94a3b8] text-xs mt-0.5">Điền đầy đủ thông tin</p>
              </div>
              <button onClick={() => setShowModal(false)} className="w-8 h-8 rounded-lg hover:bg-[#eff6ff] flex items-center justify-center text-[#94a3b8]"><XCircle size={18} /></button>
            </div>
            <div className="space-y-3">
              {["Họ và tên", "Số điện thoại", "Email"].map(f => (
                <div key={f}>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">{f}</label>
                  <input className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] focus:ring-2 focus:ring-blue-100 bg-[#eff6ff] transition-all" placeholder={`Nhập ${f.toLowerCase()}`} />
                </div>
              ))}
              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Ngày sinh</label>
                <input type="date" className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff]" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Ghi chú</label>
                <textarea rows={2} className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff] resize-none transition-all" placeholder="Thông tin thêm..." />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowModal(false)} className="flex-1 px-4 py-2.5 border border-[#bfdbfe] rounded-xl text-sm text-[#475569] hover:bg-[#eff6ff] font-medium">Hủy</button>
              <button onClick={() => setShowModal(false)} className="flex-1 px-4 py-2.5 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white rounded-xl text-sm font-semibold shadow-md shadow-blue-200">Lưu</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}