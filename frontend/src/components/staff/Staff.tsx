import { useState } from "react";
import { Search, Plus, Star, Phone, MapPin, Award, XCircle, Edit2, ChevronLeft, ChevronRight } from "lucide-react";

const staffList = [
  { id: 1, name: "Trần Thị Mai", role: "Senior Therapist", branch: "Quận 1", phone: "0901111111", specialties: ["Massage", "Body Treatment"], rating: 4.9, appointments: 342, joined: "01/2022", status: "active" },
  { id: 2, name: "Phạm Thị Lan", role: "Skin Specialist", branch: "Quận 3", phone: "0902222222", specialties: ["Chăm sóc da", "Facial"], rating: 4.8, appointments: 287, joined: "03/2022", status: "active" },
  { id: 3, name: "Nguyễn Thị Hạnh", role: "Therapist", branch: "Quận 7", phone: "0903333333", specialties: ["Massage", "Xông hơi"], rating: 4.7, appointments: 215, joined: "06/2022", status: "active" },
  { id: 4, name: "Lê Thị Nga", role: "Nail Technician", branch: "Quận 1", phone: "0904444444", specialties: ["Nail", "Tóc"], rating: 4.8, appointments: 398, joined: "08/2021", status: "active" },
  { id: 5, name: "Võ Thị Linh", role: "Junior Therapist", branch: "Thủ Đức", phone: "0905555555", specialties: ["Massage"], rating: 4.5, appointments: 124, joined: "01/2024", status: "active" },
  { id: 6, name: "Đỗ Thị Thanh", role: "Senior Therapist", branch: "Bình Thạnh", phone: "0906666666", specialties: ["Body Treatment", "Massage"], rating: 4.9, appointments: 276, joined: "05/2022", status: "active" },
  { id: 7, name: "Hoàng Thị Yến", role: "Skin Specialist", branch: "Quận 1", phone: "0907777777", specialties: ["Chăm sóc da"], rating: 4.6, appointments: 189, joined: "09/2023", status: "active" },
  { id: 8, name: "Bùi Thị Kim", role: "Therapist", branch: "Quận 3", phone: "0908888888", specialties: ["Massage", "Xông hơi"], rating: 4.7, appointments: 156, joined: "11/2023", status: "off" },
  { id: 9, name: "Lý Thị Hoa", role: "Nail Technician", branch: "Quận 7", phone: "0909999999", specialties: ["Nail"], rating: 4.5, appointments: 201, joined: "02/2023", status: "active" },
  { id: 10, name: "Trương Thị Dung", role: "Junior Therapist", branch: "Thủ Đức", phone: "0900000000", specialties: ["Massage"], rating: 4.4, appointments: 89, joined: "06/2024", status: "active" },
];

const roleStyles: Record<string, { bg: string; color: string }> = {
  "Senior Therapist": { bg: "bg-blue-50", color: "text-blue-700" },
  "Therapist": { bg: "bg-indigo-50", color: "text-indigo-700" },
  "Junior Therapist": { bg: "bg-sky-50", color: "text-sky-700" },
  "Skin Specialist": { bg: "bg-violet-50", color: "text-violet-700" },
  "Nail Technician": { bg: "bg-pink-50", color: "text-pink-700" },
};

const avatarGradients = [
  "from-[#3b82f6] to-[#60a5fa]",
  "from-[#38bdf8] to-[#7dd3fc]",
  "from-[#60a5fa] to-[#93c5fd]",
  "from-[#0ea5e9] to-[#38bdf8]",
  "from-[#3b82f6] to-[#93c5fd]",
  "from-[#0e7490] to-[#06b6d4]",
];

const branches = ["Tất cả chi nhánh", "Quận 1", "Quận 3", "Quận 7", "Thủ Đức", "Bình Thạnh"];

export function Staff() {
  const [search, setSearch] = useState("");
  const [branch, setBranch] = useState("Tất cả chi nhánh");
  const [showModal, setShowModal] = useState(false);
  const [view, setView] = useState<"grid" | "table">("grid");

  const filtered = staffList.filter((s) => {
    const matchSearch = s.name.toLowerCase().includes(search.toLowerCase()) || s.role.toLowerCase().includes(search.toLowerCase());
    const matchBranch = branch === "Tất cả chi nhánh" || s.branch === branch;
    return matchSearch && matchBranch;
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-[#64748b] text-sm">Quản lý đội ngũ nhân viên toàn hệ thống</p>
        <div className="flex items-center gap-2">
          <div className="flex bg-white border border-[#bfdbfe] rounded-xl overflow-hidden">
            <button onClick={() => setView("grid")} className={`px-3 py-2 text-xs font-medium transition-colors ${view === "grid" ? "bg-[#3b82f6] text-white" : "text-[#64748b] hover:bg-[#eff6ff]"}`}>Lưới</button>
            <button onClick={() => setView("table")} className={`px-3 py-2 text-xs font-medium transition-colors ${view === "table" ? "bg-[#3b82f6] text-white" : "text-[#64748b] hover:bg-[#eff6ff]"}`}>Bảng</button>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 bg-gradient-to-r from-[#3b82f6] to-[#60a5fa] text-white px-4 py-2.5 rounded-xl hover:opacity-90 text-sm font-medium shadow-md shadow-blue-200"
          >
            <Plus size={16} /> Thêm nhân viên
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Tổng nhân viên", value: staffList.length, color: "text-[#1d4ed8]", bg: "bg-blue-50", border: "border-blue-100" },
          { label: "Đang làm việc", value: staffList.filter(s => s.status === "active").length, color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-100" },
          { label: "Nghỉ phép", value: staffList.filter(s => s.status === "off").length, color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-100" },
          { label: "Đánh giá TB", value: (staffList.reduce((a, s) => a + s.rating, 0) / staffList.length).toFixed(1) + " ★", color: "text-amber-600", bg: "bg-amber-50", border: "border-amber-100" },
        ].map((item) => (
          <div key={item.label} className={`${item.bg} border ${item.border} rounded-xl p-4`}>
            <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
            <div className="text-xs text-[#64748b] font-medium mt-0.5">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#dbeafe] flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2 bg-[#eff6ff] border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 flex-1">
          <Search size={15} className="text-[#93c5fd] flex-shrink-0" />
          <input
            type="text"
            placeholder="Tìm nhân viên, vai trò..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent text-sm text-[#1e3a8a] placeholder-[#93c5fd] outline-none w-full"
          />
        </div>
        <select
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          className="bg-[#eff6ff] border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm text-[#1e3a8a] outline-none cursor-pointer"
        >
          {branches.map((b) => <option key={b}>{b}</option>)}
        </select>
      </div>

      {view === "grid" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((staff, idx) => {
            const role = roleStyles[staff.role] || { bg: "bg-gray-50", color: "text-gray-600" };
            return (
              <div key={staff.id} className="bg-white rounded-2xl p-5 shadow-sm border border-[#e8eef8] hover:shadow-md hover:border-[#bfdbfe] transition-all">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${avatarGradients[idx % avatarGradients.length]} flex items-center justify-center text-white font-bold text-base shadow-md`}>
                      {staff.name.charAt(0)}
                    </div>
                    <div>
                      <div className="font-semibold text-[#0c1e40] text-sm">{staff.name}</div>
                      <span className={`text-xs px-2 py-0.5 rounded-lg font-medium ${role.bg} ${role.color}`}>{staff.role}</span>
                    </div>
                  </div>
                  <span className={`text-xs px-2.5 py-1 rounded-lg font-semibold border ${staff.status === "active" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-amber-50 text-amber-700 border-amber-200"}`}>
                    {staff.status === "active" ? "● Đang làm" : "○ Nghỉ"}
                  </span>
                </div>

                <div className="space-y-2 mb-4 bg-[#f8faff] rounded-xl p-3">
                  <div className="flex items-center gap-2 text-xs text-[#475569]"><Phone size={11} className="text-[#3b82f6]" /> {staff.phone}</div>
                  <div className="flex items-center gap-2 text-xs text-[#475569]"><MapPin size={11} className="text-[#3b82f6]" /> Chi nhánh {staff.branch}</div>
                  <div className="flex items-center gap-2 text-xs text-[#475569]"><Award size={11} className="text-[#3b82f6]" /> Từ {staff.joined}</div>
                </div>

                <div className="flex flex-wrap gap-1.5 mb-4">
                  {staff.specialties.map((sp) => (
                    <span key={sp} className="text-xs bg-[#dbeafe] text-[#3b82f6] px-2 py-0.5 rounded-md font-medium">{sp}</span>
                  ))}
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-[#f0f4fb]">
                  <div className="flex items-center gap-1 text-xs">
                    <Star size={11} className="text-amber-400 fill-amber-400" />
                    <span className="font-bold text-[#0c1e40]">{staff.rating}</span>
                    <span className="text-[#94a3b8]">({staff.appointments} buổi)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button className="p-1.5 rounded-lg hover:bg-blue-50 text-[#94a3b8] hover:text-[#3b82f6] transition-colors"><Edit2 size={13} /></button>
                    <button className="px-3 py-1.5 bg-blue-50 text-[#3b82f6] rounded-lg text-xs font-semibold hover:bg-blue-100 transition-colors">Lịch làm</button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-[#e8eef8] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#e8eef8] bg-[#f8faff]">
                  {["Nhân viên", "Vai trò", "Chi nhánh", "Đánh giá", "Buổi phục vụ", "Trạng thái", ""].map((h, i) => (
                    <th key={i} className={`text-left px-4 py-3.5 text-xs font-semibold text-[#64748b] uppercase tracking-wider ${i === 1 ? "hidden md:table-cell" : i === 2 ? "hidden lg:table-cell" : i === 3 ? "hidden md:table-cell" : i === 4 ? "hidden lg:table-cell" : ""}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#f0f4fb]">
                {filtered.map((staff, idx) => {
                  const role = roleStyles[staff.role] || { bg: "bg-gray-50", color: "text-gray-600" };
                  return (
                    <tr key={staff.id} className="hover:bg-[#f8faff] transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className={`w-9 h-9 rounded-full bg-gradient-to-br ${avatarGradients[idx % avatarGradients.length]} flex items-center justify-center text-white text-xs font-bold`}>
                            {staff.name.charAt(0)}
                          </div>
                          <div>
                            <div className="text-sm font-semibold text-[#0c1e40]">{staff.name}</div>
                            <div className="text-xs text-[#94a3b8]">{staff.phone}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 hidden md:table-cell">
                        <span className={`text-xs px-2 py-1 rounded-lg font-medium ${role.bg} ${role.color}`}>{staff.role}</span>
                      </td>
                      <td className="px-4 py-3.5 hidden lg:table-cell"><span className="text-sm text-[#475569]">{staff.branch}</span></td>
                      <td className="px-4 py-3.5 hidden md:table-cell">
                        <div className="flex items-center gap-1 text-xs">
                          <Star size={11} className="text-amber-400 fill-amber-400" />
                          <span className="font-bold text-[#0c1e40]">{staff.rating}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 hidden lg:table-cell"><span className="text-sm text-[#475569]">{staff.appointments}</span></td>
                      <td className="px-4 py-3.5">
                        <span className={`text-xs px-2.5 py-1 rounded-lg font-semibold ${staff.status === "active" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                          {staff.status === "active" ? "Đang làm" : "Nghỉ phép"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <button className="p-1.5 rounded-lg hover:bg-blue-50 text-[#94a3b8] hover:text-[#3b82f6] transition-colors"><Edit2 size={14} /></button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between px-4 py-3.5 border-t border-[#dbeafe] bg-[#eff6ff]">
            <span className="text-xs text-[#94a3b8]">Hiển thị <span className="font-semibold text-[#475569]">{filtered.length}</span> / {staffList.length} nhân viên</span>
            <div className="flex items-center gap-1">
              <button className="w-8 h-8 rounded-lg border border-[#bfdbfe] flex items-center justify-center text-[#94a3b8] hover:bg-[#dbeafe] hover:text-[#3b82f6]"><ChevronLeft size={14} /></button>
              <button className="w-8 h-8 rounded-lg bg-[#3b82f6] text-white text-xs font-semibold">1</button>
              <button className="w-8 h-8 rounded-lg border border-[#bfdbfe] flex items-center justify-center text-[#94a3b8] hover:bg-[#dbeafe] hover:text-[#3b82f6]"><ChevronRight size={14} /></button>
            </div>
          </div>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-[#dbeafe]">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-[#1e3a8a]">Thêm nhân viên mới</h3>
                <p className="text-[#94a3b8] text-xs mt-0.5">Điền thông tin nhân viên</p>
              </div>
              <button onClick={() => setShowModal(false)} className="w-8 h-8 rounded-lg hover:bg-[#eff6ff] flex items-center justify-center text-[#94a3b8]"><XCircle size={18} /></button>
            </div>
            <div className="space-y-3">
              {["Họ và tên", "Số điện thoại", "Email"].map(f => (
                <div key={f}>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">{f}</label>
                  <input className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] focus:ring-2 focus:ring-blue-100 bg-[#eff6ff]" placeholder={`Nhập ${f.toLowerCase()}`} />
                </div>
              ))}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Vai trò</label>
                  <select className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff]">
                    {Object.keys(roleStyles).map(r => <option key={r}>{r}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#475569] mb-1.5 uppercase tracking-wide">Chi nhánh</label>
                  <select className="w-full border border-[#bfdbfe] rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-[#3b82f6] bg-[#eff6ff]">
                    {branches.slice(1).map(b => <option key={b}>{b}</option>)}
                  </select>
                </div>
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