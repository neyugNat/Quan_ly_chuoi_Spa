import { useState } from "react";
import { Search, Plus, Clock, Star, TrendingUp, Edit2, Trash2, XCircle } from "lucide-react";

const categories = ["Tất cả", "Massage", "Chăm sóc da", "Nail & Tóc", "Xông hơi", "Body Treatment", "Gói đặc biệt"];

const services = [
  { id: 1, name: "Massage toàn thân 90 phút", category: "Massage", duration: 90, price: 850000, rating: 4.9, bookings: 248, status: "active", desc: "Massage thư giãn toàn thân với tinh dầu cao cấp, giải tỏa căng thẳng hiệu quả." },
  { id: 2, name: "Massage thư giãn 60 phút", category: "Massage", duration: 60, price: 600000, rating: 4.8, bookings: 312, status: "active", desc: "Massage nhẹ nhàng cho cơ thể thoải mái và thư giãn sau ngày dài mệt mỏi." },
  { id: 3, name: "Massage đá nóng", category: "Massage", duration: 75, price: 950000, rating: 4.9, bookings: 189, status: "active", desc: "Kết hợp đá nóng núi lửa và tinh dầu thảo mộc, cải thiện tuần hoàn máu." },
  { id: 4, name: "Chăm sóc da cơ bản", category: "Chăm sóc da", duration: 60, price: 450000, rating: 4.7, bookings: 276, status: "active", desc: "Làm sạch sâu, tẩy tế bào chết và dưỡng ẩm cho da khỏe mạnh." },
  { id: 5, name: "Facial Treatment cao cấp", category: "Chăm sóc da", duration: 90, price: 1200000, rating: 4.9, bookings: 145, status: "active", desc: "Liệu trình phục hồi da chuyên sâu với công nghệ hiện đại." },
  { id: 6, name: "Chăm sóc da chuyên sâu", category: "Chăm sóc da", duration: 120, price: 980000, rating: 4.8, bookings: 98, status: "active", desc: "Điều trị các vấn đề da chuyên biệt: nám, thâm, mụn." },
  { id: 7, name: "Manicure + Pedicure", category: "Nail & Tóc", duration: 90, price: 380000, rating: 4.6, bookings: 334, status: "active", desc: "Làm móng tay và móng chân toàn diện, bao gồm sơn gel cao cấp." },
  { id: 8, name: "Xông hơi thảo dược", category: "Xông hơi", duration: 45, price: 350000, rating: 4.7, bookings: 167, status: "active", desc: "Xông hơi với thảo dược thiên nhiên, thanh lọc cơ thể và thư giãn." },
  { id: 9, name: "Xông hơi ướt phòng riêng", category: "Xông hơi", duration: 60, price: 480000, rating: 4.8, bookings: 112, status: "active", desc: "Phòng xông hơi ướt riêng tư cao cấp với tinh dầu thơm." },
  { id: 10, name: "Body Scrub & Wrap", category: "Body Treatment", duration: 90, price: 750000, rating: 4.7, bookings: 134, status: "active", desc: "Tẩy tế bào chết toàn thân và ủ khoáng nâng cao độ ẩm cho da." },
  { id: 11, name: "Gói Spa Cặp Đôi", category: "Gói đặc biệt", duration: 120, price: 1800000, rating: 5.0, bookings: 87, status: "active", desc: "Trải nghiệm spa đặc biệt cho 2 người: massage + facial + xông hơi." },
  { id: 12, name: "Gói Thư Giãn Cuối Tuần", category: "Gói đặc biệt", duration: 180, price: 2200000, rating: 4.9, bookings: 65, status: "inactive", desc: "Gói spa trọn ngày cuối tuần với đầy đủ dịch vụ cao cấp." },
];

const catStyles: Record<string, { bg: string; color: string; dot: string }> = {
  "Massage": { bg: "bg-blue-50", color: "text-blue-700", dot: "#1d4ed8" },
  "Chăm sóc da": { bg: "bg-violet-50", color: "text-violet-700", dot: "#6d28d9" },
  "Nail & Tóc": { bg: "bg-pink-50", color: "text-pink-700", dot: "#be185d" },
  "Xông hơi": { bg: "bg-teal-50", color: "text-teal-700", dot: "#0f766e" },
  "Body Treatment": { bg: "bg-amber-50", color: "text-amber-700", dot: "#b45309" },
  "Gói đặc biệt": { bg: "bg-indigo-50", color: "text-indigo-700", dot: "#4338ca" },
};

export function Services() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("Tất cả");
  const [showModal, setShowModal] = useState(false);

  const filtered = services.filter((s) => {
    const matchSearch = s.name.toLowerCase().includes(search.toLowerCase());
    const matchCat = category === "Tất cả" || s.category === category;
    return matchSearch && matchCat;
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-[#64748b] text-sm">Danh mục dịch vụ spa toàn chuỗi</p>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white px-4 py-2.5 rounded-xl hover:opacity-90 text-sm font-medium shadow-md shadow-blue-200"
        >
          <Plus size={16} /> Thêm dịch vụ
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Tổng dịch vụ", value: services.length, color: "text-[#1d4ed8]", bg: "bg-blue-50", border: "border-blue-100" },
          { label: "Đang hoạt động", value: services.filter(s => s.status === "active").length, color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-100" },
          { label: "Tổng lượt đặt", value: services.reduce((a, s) => a + s.bookings, 0).toLocaleString(), color: "text-indigo-700", bg: "bg-indigo-50", border: "border-indigo-100" },
          { label: "Đánh giá TB", value: "4.8 ★", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-100" },
        ].map((item) => (
          <div key={item.label} className={`${item.bg} border ${item.border} rounded-xl p-4`}>
            <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
            <div className="text-xs text-[#64748b] font-medium mt-0.5">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#dbeafe]">
        <div className="flex items-center gap-2 bg-[#eff6ff] border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 mb-3">
          <Search size={15} className="text-[#93c5fd] flex-shrink-0" />
          <input
            type="text"
            placeholder="Tìm tên dịch vụ..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent text-sm text-[#1e3a8a] placeholder-[#93c5fd] outline-none w-full"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${category === c ? "bg-[#3b82f6] text-white shadow-sm" : "bg-[#eff6ff] text-[#475569] hover:bg-[#dbeafe] hover:text-[#3b82f6]"}`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Service cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((svc) => {
          const cat = catStyles[svc.category] || { bg: "bg-gray-50", color: "text-gray-600", dot: "#6b7280" };
          return (
            <div key={svc.id} className={`bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8] hover:shadow-md hover:border-[#bfdbfe] transition-all ${svc.status === "inactive" ? "opacity-60" : ""}`}>
              <div className="flex items-start justify-between mb-3">
                <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg ${cat.bg} ${cat.color}`}>
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: cat.dot }} />
                  {svc.category}
                </span>
                <div className="flex items-center gap-1">
                  <button className="p-1.5 rounded-lg hover:bg-blue-50 text-[#94a3b8] hover:text-[#1d4ed8] transition-colors"><Edit2 size={13} /></button>
                  <button className="p-1.5 rounded-lg hover:bg-red-50 text-[#94a3b8] hover:text-red-500 transition-colors"><Trash2 size={13} /></button>
                </div>
              </div>

              <h3 className="text-[#0c1e40] text-sm font-semibold mb-1.5 leading-snug">{svc.name}</h3>
              <p className="text-xs text-[#94a3b8] mb-4 leading-relaxed line-clamp-2">{svc.desc}</p>

              <div className="grid grid-cols-3 gap-2 mb-4">
                {[
                  { icon: <Clock size={11} className="text-[#3b82f6]" />, value: `${svc.duration}'`, label: "Thời gian" },
                  { icon: <Star size={11} className="text-amber-400 fill-amber-400" />, value: svc.rating, label: "Đánh giá" },
                  { icon: <TrendingUp size={11} className="text-[#3b82f6]" />, value: svc.bookings, label: "Lượt đặt" },
                ].map((stat, i) => (
                  <div key={i} className="text-center bg-[#f8faff] rounded-xl py-2.5">
                    <div className="flex items-center justify-center gap-1 text-xs font-bold text-[#0c1e40]">
                      {stat.icon} {stat.value}
                    </div>
                    <div className="text-xs text-[#94a3b8] mt-0.5">{stat.label}</div>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-[#f0f4fb]">
                <div className="text-lg font-bold text-[#3b82f6]">{svc.price.toLocaleString()}đ</div>
                <span className={`text-xs px-2.5 py-1 rounded-lg font-semibold ${svc.status === "active" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-slate-100 text-slate-500 border border-slate-200"}`}>
                  {svc.status === "active" ? "● Hoạt động" : "○ Tạm dừng"}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-[#dbeafe]">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-[#1e3a8a]">Thêm dịch vụ mới</h3>
                <p className="text-[#94a3b8] text-xs mt-0.5">Điền thông tin dịch vụ</p>
              </div>
              <button onClick={() => setShowModal(false)} className="w-8 h-8 rounded-lg hover:bg-[#eff6ff] flex items-center justify-center text-[#94a3b8]"><XCircle size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Tên dịch vụ</label>
                <input className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] focus:ring-2 focus:ring-blue-100 bg-[#eff6ff]" placeholder="Nhập tên dịch vụ" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Danh mục</label>
                <select className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff]">
                  {categories.slice(1).map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Thời gian (phút)</label>
                  <input type="number" className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff]" placeholder="60" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Giá (đồng)</label>
                  <input type="number" className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff]" placeholder="500000" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Mô tả</label>
                <textarea rows={3} className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff] resize-none" placeholder="Mô tả chi tiết..." />
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