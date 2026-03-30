import { useState } from "react";
import { MapPin, Phone, Clock, Users, Star, Edit2, Plus, XCircle, CheckCircle2, Building2 } from "lucide-react";

const branches = [
  { id: 1, name: "Lotus Spa — Quận 1", short: "Q.1", address: "25 Nguyễn Huệ, Phường Bến Nghé, Quận 1, TP.HCM", phone: "028-3822-1111", hours: "08:00 – 22:00", manager: "Nguyễn Thị Hương", staff: 18, rooms: 8, rating: 4.9, revenue: "195,4 tr", appointments: 148, established: "01/2020", image: "https://images.unsplash.com/photo-1633526543913-d30e3c230d1f?w=400&q=80" },
  { id: 2, name: "Lotus Spa — Quận 3", short: "Q.3", address: "88 Võ Văn Tần, Phường 6, Quận 3, TP.HCM", phone: "028-3933-2222", hours: "08:00 – 22:00", manager: "Trần Thị Bích", staff: 15, rooms: 6, rating: 4.8, revenue: "162 tr", appointments: 122, established: "06/2020", image: "https://images.unsplash.com/photo-1700142360825-d21edc53c8db?w=400&q=80" },
  { id: 3, name: "Lotus Spa — Quận 7", short: "Q.7", address: "120 Nguyễn Thị Thập, Phường Tân Phú, Quận 7, TP.HCM", phone: "028-5412-3333", hours: "09:00 – 21:30", manager: "Lê Thị Phương", staff: 14, rooms: 6, rating: 4.7, revenue: "148 tr", appointments: 108, established: "01/2021", image: "https://images.unsplash.com/photo-1633526543913-d30e3c230d1f?w=400&q=80" },
  { id: 4, name: "Lotus Spa — Thủ Đức", short: "T.Đ", address: "56 Võ Văn Ngân, Phường Bình Thọ, TP. Thủ Đức, TP.HCM", phone: "028-7300-4444", hours: "08:30 – 21:00", manager: "Phạm Thị Xuân", staff: 12, rooms: 5, rating: 4.6, revenue: "125 tr", appointments: 92, established: "08/2022", image: "https://images.unsplash.com/photo-1700142360825-d21edc53c8db?w=400&q=80" },
  { id: 5, name: "Lotus Spa — Bình Thạnh", short: "B.T", address: "42 Đinh Tiên Hoàng, Phường 3, Quận Bình Thạnh, TP.HCM", phone: "028-3515-5555", hours: "08:00 – 21:30", manager: "Hoàng Thị Liên", staff: 13, rooms: 5, rating: 4.7, revenue: "110 tr", appointments: 85, established: "03/2023", image: "https://images.unsplash.com/photo-1633526543913-d30e3c230d1f?w=400&q=80" },
];

export function Branches() {
  const [selected, setSelected] = useState<typeof branches[0] | null>(null);
  const [showModal, setShowModal] = useState(false);

  const totalStaff = branches.reduce((a, b) => a + b.staff, 0);
  const totalRooms = branches.reduce((a, b) => a + b.rooms, 0);
  const avgRating = (branches.reduce((a, b) => a + b.rating, 0) / branches.length).toFixed(1);

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-[#64748b] text-sm">Quản lý thông tin các chi nhánh trong chuỗi</p>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white px-4 py-2.5 rounded-xl hover:opacity-90 text-sm font-medium shadow-md shadow-blue-200"
        >
          <Plus size={16} /> Mở chi nhánh mới
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Chi nhánh hoạt động", value: branches.length, color: "text-[#1d4ed8]", bg: "bg-blue-50", border: "border-blue-100" },
          { label: "Tổng nhân viên", value: totalStaff, color: "text-indigo-700", bg: "bg-indigo-50", border: "border-indigo-100" },
          { label: "Tổng phòng trị liệu", value: totalRooms, color: "text-cyan-700", bg: "bg-cyan-50", border: "border-cyan-100" },
          { label: "Đánh giá trung bình", value: avgRating + " ★", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-100" },
        ].map((item) => (
          <div key={item.label} className={`${item.bg} border ${item.border} rounded-xl p-4`}>
            <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
            <div className="text-xs text-[#64748b] font-medium mt-0.5">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Branch cards */}
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
              {/* Branch number badge */}
              <div className="absolute top-3 left-3 w-8 h-8 rounded-lg bg-[#1d4ed8] flex items-center justify-center text-white text-xs font-bold shadow">
                {idx + 1}
              </div>
              <div className="absolute top-3 right-3 flex items-center gap-1 bg-emerald-500 text-white text-xs font-semibold px-2.5 py-1 rounded-full shadow">
                <CheckCircle2 size={10} /> Hoạt động
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
                  { label: "NV", value: branch.staff },
                  { label: "Phòng", value: branch.rooms },
                  { label: "Lịch hẹn", value: branch.appointments },
                  { label: "DT", value: branch.revenue },
                ].map((stat, i) => (
                  <div key={i} className="text-center bg-[#f8faff] border border-[#e8eef8] rounded-xl py-2">
                    <div className="text-xs font-bold text-[#0c1e40]">{stat.value}</div>
                    <div className="text-xs text-[#94a3b8]" style={{ fontSize: "10px" }}>{stat.label}</div>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-[#f0f4fb]">
                <span className="text-xs text-[#94a3b8]">
                  Quản lý: <span className="text-[#0c1e40] font-semibold">{branch.manager}</span>
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); }}
                  className="flex items-center gap-1.5 text-xs text-[#1d4ed8] font-semibold bg-blue-50 px-3 py-1.5 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <Edit2 size={11} /> Chỉnh sửa
                </button>
              </div>
            </div>
          </div>
        ))}

        {/* Add placeholder */}
        <div
          className="border-2 border-dashed border-[#bfdbfe] rounded-2xl flex flex-col items-center justify-center p-10 cursor-pointer hover:border-[#1d4ed8] hover:bg-[#f0f4fb] transition-all group"
          onClick={() => setShowModal(true)}
        >
          <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-[#bfdbfe] flex items-center justify-center mb-3 group-hover:bg-blue-100 transition-colors">
            <Building2 size={24} className="text-[#1d4ed8]" />
          </div>
          <div className="text-sm font-semibold text-[#1d4ed8]">Mở chi nhánh mới</div>
          <div className="text-xs text-[#94a3b8] mt-1">Mở rộng chuỗi Lotus Spa</div>
        </div>
      </div>

      {/* Detail modal */}
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
                  Hoạt động từ {selected.established}
                </div>
              </div>
            </div>
            <div className="p-5">
              <div className="grid grid-cols-2 gap-3 mb-4">
                {[
                  { label: "Nhân viên", value: selected.staff + " người" },
                  { label: "Phòng trị liệu", value: selected.rooms + " phòng" },
                  { label: "Lịch hẹn tháng", value: selected.appointments },
                  { label: "Doanh thu tháng", value: selected.revenue },
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
                <button className="flex-1 px-4 py-2.5 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white rounded-xl text-sm font-semibold shadow-md shadow-blue-200">Chỉnh sửa</button>
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
                <h3 className="text-[#1e3a8a]">Mở chi nhánh mới</h3>
                <p className="text-[#94a3b8] text-xs mt-0.5">Điền thông tin chi nhánh</p>
              </div>
              <button onClick={() => setShowModal(false)} className="w-8 h-8 rounded-lg hover:bg-[#eff6ff] flex items-center justify-center text-[#94a3b8]"><XCircle size={18} /></button>
            </div>
            <div className="space-y-3">
              {["Tên chi nhánh", "Địa chỉ", "Số điện thoại", "Tên quản lý"].map(f => (
                <div key={f}>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">{f}</label>
                  <input className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] focus:ring-2 focus:ring-blue-100 bg-[#eff6ff]" placeholder={`Nhập ${f.toLowerCase()}`} />
                </div>
              ))}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Giờ mở cửa</label>
                  <input type="time" defaultValue="08:00" className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff]" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Giờ đóng cửa</label>
                  <input type="time" defaultValue="22:00" className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff]" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowModal(false)} className="flex-1 px-4 py-2.5 border border-[#bfdbfe] rounded-xl text-sm text-[#475569] hover:bg-[#eff6ff] font-medium">Hủy</button>
              <button onClick={() => setShowModal(false)} className="flex-1 px-4 py-2.5 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white rounded-xl text-sm font-semibold shadow-md shadow-blue-200">Thêm chi nhánh</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}