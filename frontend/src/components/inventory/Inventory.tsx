import { useState } from "react";
import {
  Package, Plus, Search, Edit2, Trash2, XCircle, ChevronLeft, ChevronRight,
  AlertTriangle, TrendingDown, TrendingUp, ShoppingCart, BarChart2,
  ArrowUpCircle, ArrowDownCircle, Filter, Download, RefreshCw,
} from "lucide-react";

type ItemStatus = "in_stock" | "low" | "out_of_stock";
type Category = "Dầu massage" | "Dưỡng da" | "Vệ sinh" | "Dụng cụ" | "Tiêu hao" | "Khăn & Ga";

interface InventoryItem {
  id: string;
  name: string;
  sku: string;
  category: Category;
  unit: string;
  quantity: number;
  minStock: number;
  maxStock: number;
  costPrice: number;
  supplier: string;
  branch: string;
  lastUpdated: string;
  status: ItemStatus;
}

interface Transaction {
  id: string;
  date: string;
  itemName: string;
  type: "import" | "export" | "adjust";
  quantity: number;
  by: string;
  note: string;
}

const statusConfig: Record<ItemStatus, { label: string; color: string; bg: string; border: string; dot: string }> = {
  in_stock:     { label: "Còn hàng",   color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200", dot: "bg-emerald-500" },
  low:          { label: "Sắp hết",    color: "text-amber-700",   bg: "bg-amber-50",   border: "border-amber-200",   dot: "bg-amber-500" },
  out_of_stock: { label: "Hết hàng",   color: "text-red-700",     bg: "bg-red-50",     border: "border-red-200",     dot: "bg-red-500" },
};

const categoryColors: Record<Category, string> = {
  "Dầu massage": "bg-violet-100 text-violet-700",
  "Dưỡng da":    "bg-pink-100 text-pink-700",
  "Vệ sinh":     "bg-cyan-100 text-cyan-700",
  "Dụng cụ":     "bg-orange-100 text-orange-700",
  "Tiêu hao":    "bg-gray-100 text-gray-600",
  "Khăn & Ga":   "bg-blue-100 text-blue-700",
};

const mockItems: InventoryItem[] = [
  { id: "INV001", name: "Dầu massage oải hương", sku: "OIL-LAV-500", category: "Dầu massage", unit: "Chai", quantity: 48, minStock: 20, maxStock: 100, costPrice: 185000, supplier: "Spa Supplies VN", branch: "Quận 1", lastUpdated: "26/03/2026", status: "in_stock" },
  { id: "INV002", name: "Dầu massage bạc hà", sku: "OIL-MINT-500", category: "Dầu massage", unit: "Chai", quantity: 12, minStock: 20, maxStock: 80, costPrice: 175000, supplier: "Spa Supplies VN", branch: "Quận 1", lastUpdated: "25/03/2026", status: "low" },
  { id: "INV003", name: "Kem dưỡng trắng da", sku: "CREAM-WHT-200", category: "Dưỡng da", unit: "Hộp", quantity: 35, minStock: 15, maxStock: 60, costPrice: 320000, supplier: "BeautyPro", branch: "Quận 3", lastUpdated: "27/03/2026", status: "in_stock" },
  { id: "INV004", name: "Gel tẩy tế bào chết", sku: "GEL-EXF-150", category: "Dưỡng da", unit: "Tuýp", quantity: 0, minStock: 10, maxStock: 50, costPrice: 280000, supplier: "BeautyPro", branch: "Quận 7", lastUpdated: "20/03/2026", status: "out_of_stock" },
  { id: "INV005", name: "Khăn bông cao cấp", sku: "TWL-WHT-70x140", category: "Khăn & Ga", unit: "Cái", quantity: 245, minStock: 100, maxStock: 400, costPrice: 95000, supplier: "Textile House", branch: "Tất cả", lastUpdated: "27/03/2026", status: "in_stock" },
  { id: "INV006", name: "Ga trải giường spa", sku: "BED-WHT-160x220", category: "Khăn & Ga", unit: "Cái", quantity: 18, minStock: 30, maxStock: 120, costPrice: 220000, supplier: "Textile House", branch: "Tất cả", lastUpdated: "24/03/2026", status: "low" },
  { id: "INV007", name: "Cồn sát khuẩn 70%", sku: "ALC-70-1L", category: "Vệ sinh", unit: "Chai", quantity: 60, minStock: 30, maxStock: 150, costPrice: 45000, supplier: "MedSupply", branch: "Tất cả", lastUpdated: "27/03/2026", status: "in_stock" },
  { id: "INV008", name: "Nước tẩy dụng cụ", sku: "CLN-INST-5L", category: "Vệ sinh", unit: "Can", quantity: 8, minStock: 10, maxStock: 40, costPrice: 180000, supplier: "MedSupply", branch: "Tất cả", lastUpdated: "22/03/2026", status: "low" },
  { id: "INV009", name: "Đá nóng basalt", sku: "STN-BSL-SET", category: "Dụng cụ", unit: "Bộ", quantity: 15, minStock: 5, maxStock: 30, costPrice: 850000, supplier: "Spa Tools Pro", branch: "Quận 1", lastUpdated: "15/03/2026", status: "in_stock" },
  { id: "INV010", name: "Muối Himalaya hồng", sku: "SALT-HIM-1KG", category: "Tiêu hao", unit: "Kg", quantity: 32, minStock: 20, maxStock: 100, costPrice: 125000, supplier: "NaturalPure", branch: "Tất cả", lastUpdated: "26/03/2026", status: "in_stock" },
  { id: "INV011", name: "Dầu dừa nguyên chất", sku: "OIL-COC-1L", category: "Dầu massage", unit: "Chai", quantity: 5, minStock: 15, maxStock: 60, costPrice: 210000, supplier: "NaturalPure", branch: "Quận 7", lastUpdated: "21/03/2026", status: "low" },
  { id: "INV012", name: "Mặt nạ đất sét", sku: "MASK-CLY-500", category: "Dưỡng da", unit: "Hũ", quantity: 0, minStock: 8, maxStock: 30, costPrice: 390000, supplier: "BeautyPro", branch: "Bình Thạnh", lastUpdated: "18/03/2026", status: "out_of_stock" },
];

const mockTransactions: Transaction[] = [
  { id: "TX001", date: "27/03/2026 09:15", itemName: "Dầu massage oải hương", type: "import", quantity: 24, by: "Trần Thị Hoa", note: "Nhập hàng theo PO-2026-031" },
  { id: "TX002", date: "27/03/2026 08:30", itemName: "Khăn bông cao cấp", type: "export", quantity: 20, by: "Phạm Thu Hằng", note: "Xuất cho ca sáng CN Quận 1" },
  { id: "TX003", date: "26/03/2026 17:45", itemName: "Muối Himalaya hồng", type: "export", quantity: 5, by: "Võ Thị Lan", note: "Dùng cho liệu trình detox" },
  { id: "TX004", date: "26/03/2026 14:20", itemName: "Cồn sát khuẩn 70%", type: "import", quantity: 30, by: "Lê Minh Tuấn", note: "Nhập hàng thường kỳ" },
  { id: "TX005", date: "25/03/2026 11:00", itemName: "Gel tẩy tế bào chết", type: "adjust", quantity: -3, by: "Admin", note: "Điều chỉnh kiểm kê thực tế" },
  { id: "TX006", date: "25/03/2026 09:30", itemName: "Đá nóng basalt", type: "import", quantity: 2, by: "Trần Thị Hoa", note: "Bổ sung bộ đá cho CN mới" },
];

const categories = ["Tất cả", "Dầu massage", "Dưỡng da", "Vệ sinh", "Dụng cụ", "Tiêu hao", "Khăn & Ga"];

function StockBar({ quantity, minStock, maxStock }: { quantity: number; minStock: number; maxStock: number }) {
  const pct = Math.min((quantity / maxStock) * 100, 100);
  const color = quantity === 0 ? "bg-red-400" : quantity <= minStock ? "bg-amber-400" : "bg-emerald-400";
  return (
    <div className="w-full bg-gray-100 rounded-full h-1.5">
      <div className={`h-1.5 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Inventory() {
  const [items] = useState<InventoryItem[]>(mockItems);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("Tất cả");
  const [statusFilter, setStatusFilter] = useState("Tất cả");
  const [activeTab, setActiveTab] = useState<"list" | "transactions">("list");
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState<InventoryItem | null>(null);
  const [deleteItem, setDeleteItem] = useState<InventoryItem | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);

  const filtered = items.filter(item => {
    const q = search.toLowerCase();
    const matchQ = item.name.toLowerCase().includes(q) || item.sku.toLowerCase().includes(q) || item.supplier.toLowerCase().includes(q);
    const matchCat = category === "Tất cả" || item.category === category;
    const matchStatus = statusFilter === "Tất cả"
      || (statusFilter === "Còn hàng" && item.status === "in_stock")
      || (statusFilter === "Sắp hết" && item.status === "low")
      || (statusFilter === "Hết hàng" && item.status === "out_of_stock");
    return matchQ && matchCat && matchStatus;
  });

  const counts = {
    total: items.length,
    low: items.filter(i => i.status === "low").length,
    out: items.filter(i => i.status === "out_of_stock").length,
    totalValue: items.reduce((sum, i) => sum + i.quantity * i.costPrice, 0),
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-gray-500 text-sm">Theo dõi tồn kho & lưu chuyển vật dụng spa</p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowImportModal(true)}
            className="flex items-center gap-2 border border-gray-200 bg-white/80 text-gray-600 px-3.5 py-2.5 rounded-xl hover:bg-gray-50 text-sm font-semibold transition-all hover:scale-105"
          >
            <ArrowUpCircle size={15} className="text-emerald-500" /> Nhập kho
          </button>
          <button
            onClick={() => { setEditItem(null); setShowModal(true); }}
            className="flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-4 py-2.5 rounded-xl hover:opacity-90 text-sm font-semibold shadow-md shadow-emerald-200 transition-all hover:scale-105"
          >
            <Plus size={16} /> Thêm mặt hàng
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Tổng mặt hàng", value: counts.total, icon: Package, color: "text-blue-600", bg: "bg-blue-50", border: "border-blue-100", gradient: "from-blue-400 to-cyan-400" },
          { label: "Sắp hết hàng", value: counts.low, icon: AlertTriangle, color: "text-amber-600", bg: "bg-amber-50", border: "border-amber-100", gradient: "from-amber-400 to-orange-400" },
          { label: "Hết hàng", value: counts.out, icon: TrendingDown, color: "text-red-600", bg: "bg-red-50", border: "border-red-100", gradient: "from-red-400 to-pink-400" },
          { label: "Giá trị tồn kho", value: `${(counts.totalValue / 1_000_000).toFixed(1)} tr₫`, icon: BarChart2, color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100", gradient: "from-emerald-400 to-teal-400" },
        ].map(stat => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className={`${stat.bg} border ${stat.border} rounded-2xl p-4 flex items-center gap-3 group hover:shadow-md transition-shadow`}>
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center flex-shrink-0 shadow-sm`}>
                <Icon size={18} className="text-white" />
              </div>
              <div>
                <div className={`text-xl font-bold ${stat.color}`}>{stat.value}</div>
                <div className="text-xs text-gray-500 font-medium">{stat.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Low stock alert */}
      {counts.low > 0 || counts.out > 0 ? (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-sm font-semibold text-amber-800">Cảnh báo tồn kho</div>
            <div className="text-xs text-amber-700 mt-0.5">
              Có <strong>{counts.low}</strong> mặt hàng sắp hết và <strong>{counts.out}</strong> mặt hàng đã hết hàng. Cần đặt hàng bổ sung ngay.
              {" "}<button className="underline font-semibold hover:text-amber-900">Xem danh sách →</button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Tabs */}
      <div className="flex gap-1 bg-white/60 backdrop-blur border border-white/60 rounded-xl p-1 w-fit shadow-sm">
        {[{ id: "list", label: "📦 Danh sách kho" }, { id: "transactions", label: "🔄 Lịch sử xuất nhập" }].map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id as any)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === t.id ? "bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-sm" : "text-gray-500 hover:text-gray-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "list" && (
        <>
          {/* Filters */}
          <div className="bg-white/80 backdrop-blur rounded-2xl p-4 shadow-sm border border-white/60 space-y-3">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 flex-1">
                <Search size={15} className="text-gray-400 flex-shrink-0" />
                <input type="text" placeholder="Tìm tên, SKU, nhà cung cấp..." value={search} onChange={e => setSearch(e.target.value)}
                  className="bg-transparent text-sm text-gray-700 placeholder-gray-400 outline-none w-full" />
              </div>
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5 text-sm text-gray-700 outline-none cursor-pointer">
                {["Tất cả", "Còn hàng", "Sắp hết", "Hết hàng"].map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex gap-2 flex-wrap">
              {categories.map(c => (
                <button key={c} onClick={() => setCategory(c)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${category === c ? "bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-sm" : "bg-gray-100 text-gray-500 hover:bg-emerald-50 hover:text-emerald-600"}`}>
                  {c}
                </button>
              ))}
            </div>
          </div>

          {/* Table */}
          <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/80">
                    {["Mặt hàng", "SKU", "Danh mục", "Tồn kho", "Mức tồn", "Đơn giá", "Nhà CC", "Trạng thái", ""].map((h, i) => (
                      <th key={i} className={`text-left px-4 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap
                        ${i === 1 ? "hidden lg:table-cell" : i === 2 ? "hidden md:table-cell" : i === 4 ? "hidden md:table-cell" : i === 6 ? "hidden xl:table-cell" : ""}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filtered.map(item => {
                    const st = statusConfig[item.status];
                    return (
                      <tr key={item.id} className="hover:bg-emerald-50/30 transition-colors group">
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-3">
                            <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${categoryColors[item.category]}`}>
                              <Package size={15} />
                            </div>
                            <div>
                              <div className="text-sm font-semibold text-gray-800">{item.name}</div>
                              <div className="text-xs text-gray-400">{item.unit} · {item.branch}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 hidden lg:table-cell">
                          <span className="font-mono text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">{item.sku}</span>
                        </td>
                        <td className="px-4 py-3.5 hidden md:table-cell">
                          <span className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${categoryColors[item.category]}`}>{item.category}</span>
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2 min-w-[100px]">
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-1">
                                <span className={`text-sm font-bold ${item.status === "out_of_stock" ? "text-red-600" : item.status === "low" ? "text-amber-600" : "text-gray-800"}`}>
                                  {item.quantity}
                                </span>
                                <span className="text-xs text-gray-400">/{item.maxStock}</span>
                              </div>
                              <StockBar quantity={item.quantity} minStock={item.minStock} maxStock={item.maxStock} />
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 hidden md:table-cell">
                          <div className="text-xs text-gray-500">
                            <span className="text-red-500">Min: {item.minStock}</span>
                            <span className="text-gray-300 mx-1">|</span>
                            <span className="text-emerald-500">Max: {item.maxStock}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="text-sm font-bold text-gray-700">{item.costPrice.toLocaleString()}đ</div>
                          <div className="text-xs text-gray-400">/{item.unit}</div>
                        </td>
                        <td className="px-4 py-3.5 hidden xl:table-cell">
                          <div className="text-xs text-gray-600">{item.supplier}</div>
                          <div className="text-xs text-gray-400">{item.lastUpdated}</div>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg border ${st.bg} ${st.color} ${st.border}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${st.dot} ${item.status === "low" ? "animate-pulse" : ""}`} />
                            {st.label}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button onClick={() => { setEditItem(item); setShowModal(true); }} className="p-1.5 rounded-lg hover:bg-emerald-100 text-gray-400 hover:text-emerald-600 transition-colors" title="Sửa"><Edit2 size={13} /></button>
                            <button onClick={() => setDeleteItem(item)} className="p-1.5 rounded-lg hover:bg-red-100 text-gray-400 hover:text-red-500 transition-colors" title="Xóa"><Trash2 size={13} /></button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between px-4 py-3.5 border-t border-gray-100 bg-gray-50/50">
              <span className="text-xs text-gray-400">Hiển thị <span className="font-semibold text-gray-600">{filtered.length}</span> / {items.length} mặt hàng</span>
              <div className="flex items-center gap-1">
                <button className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400 hover:bg-emerald-50 hover:text-emerald-600 transition-colors"><ChevronLeft size={14} /></button>
                <button className="w-8 h-8 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-xs font-semibold">1</button>
                <button className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400 hover:bg-emerald-50 hover:text-emerald-600 transition-colors"><ChevronRight size={14} /></button>
              </div>
            </div>
          </div>
        </>
      )}

      {activeTab === "transactions" && (
        <div className="bg-white/80 backdrop-blur rounded-2xl shadow-sm border border-white/60 overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-gray-100">
            <div>
              <h3 className="text-sm font-semibold text-gray-700">Lịch sử xuất nhập kho</h3>
              <p className="text-xs text-gray-400 mt-0.5">30 ngày gần nhất</p>
            </div>
            <button className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50">
              <Download size={12} /> Xuất Excel
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/80">
                  {["Mã GD", "Thời gian", "Mặt hàng", "Loại", "Số lượng", "Người thực hiện", "Ghi chú"].map((h, i) => (
                    <th key={i} className={`text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider ${i === 0 ? "hidden md:table-cell" : i === 6 ? "hidden lg:table-cell" : ""}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {mockTransactions.map(tx => {
                  const typeConfig = {
                    import: { label: "Nhập kho", icon: ArrowUpCircle, color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200" },
                    export: { label: "Xuất kho", icon: ArrowDownCircle, color: "text-blue-700", bg: "bg-blue-50 border-blue-200" },
                    adjust: { label: "Điều chỉnh", icon: RefreshCw, color: "text-amber-700", bg: "bg-amber-50 border-amber-200" },
                  }[tx.type];
                  const TIcon = typeConfig.icon;
                  return (
                    <tr key={tx.id} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-4 py-3 hidden md:table-cell">
                        <span className="font-mono text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">{tx.id}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-xs font-medium text-gray-700">{tx.date}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm text-gray-700 font-medium">{tx.itemName}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg border ${typeConfig.bg} ${typeConfig.color}`}>
                          <TIcon size={11} />{typeConfig.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-sm font-bold ${tx.quantity > 0 ? "text-emerald-600" : "text-red-500"}`}>
                          {tx.quantity > 0 ? `+${tx.quantity}` : tx.quantity}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-xs text-gray-600">{tx.by}</div>
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <div className="text-xs text-gray-400 max-w-[200px] truncate">{tx.note}</div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 border border-gray-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-gray-900 font-semibold">{editItem ? "Chỉnh sửa mặt hàng" : "Thêm mặt hàng mới"}</h3>
                <p className="text-gray-400 text-xs mt-0.5">Điền thông tin chi tiết mặt hàng</p>
              </div>
              <button onClick={() => { setShowModal(false); setEditItem(null); }} className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center text-gray-400"><XCircle size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Tên mặt hàng *</label>
                <input defaultValue={editItem?.name} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 bg-gray-50" placeholder="Nhập tên mặt hàng" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">SKU</label>
                  <input defaultValue={editItem?.sku} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50 font-mono" placeholder="SKU-XXX" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Đơn vị</label>
                  <input defaultValue={editItem?.unit} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50" placeholder="Chai, Hộp, Cái..." />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Danh mục</label>
                  <select defaultValue={editItem?.category} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50 cursor-pointer">
                    {categories.slice(1).map(c => <option key={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Đơn giá (₫)</label>
                  <input type="number" defaultValue={editItem?.costPrice} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50" placeholder="0" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Tồn kho tối thiểu</label>
                  <input type="number" defaultValue={editItem?.minStock} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Tồn kho tối đa</label>
                  <input type="number" defaultValue={editItem?.maxStock} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Nhà cung cấp</label>
                <input defaultValue={editItem?.supplier} className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50" placeholder="Tên nhà cung cấp" />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => { setShowModal(false); setEditItem(null); }} className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 font-medium">Hủy</button>
              <button onClick={() => { setShowModal(false); setEditItem(null); }} className="flex-1 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl text-sm font-semibold shadow-md shadow-emerald-200 hover:opacity-90">
                {editItem ? "Lưu thay đổi" : "Thêm mặt hàng"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-100">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-gray-900 font-semibold">Nhập kho nhanh</h3>
                <p className="text-gray-400 text-xs mt-0.5">Cập nhật số lượng nhập</p>
              </div>
              <button onClick={() => setShowImportModal(false)} className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center text-gray-400"><XCircle size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Mặt hàng</label>
                <select className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50 cursor-pointer">
                  {items.map(i => <option key={i.id}>{i.name}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Số lượng nhập</label>
                  <input type="number" className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50" placeholder="0" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Chi nhánh</label>
                  <select className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50 cursor-pointer">
                    <option>Quận 1</option><option>Quận 3</option><option>Quận 7</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Mã phiếu nhập / Ghi chú</label>
                <input className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm outline-none focus:border-emerald-400 bg-gray-50" placeholder="PO-2026-xxx hoặc ghi chú..." />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowImportModal(false)} className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 font-medium">Hủy</button>
              <button onClick={() => setShowImportModal(false)} className="flex-1 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl text-sm font-semibold shadow-md shadow-emerald-200 hover:opacity-90">Xác nhận nhập kho</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteItem && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 border border-gray-100">
            <div className="text-center mb-5">
              <div className="w-14 h-14 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-3"><Trash2 size={24} className="text-red-500" /></div>
              <h3 className="text-gray-900 font-semibold">Xóa mặt hàng?</h3>
              <p className="text-gray-500 text-sm mt-2">Xóa <strong className="text-gray-800">{deleteItem.name}</strong> khỏi kho?</p>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setDeleteItem(null)} className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 font-medium">Hủy</button>
              <button onClick={() => setDeleteItem(null)} className="flex-1 px-4 py-2.5 bg-red-500 text-white rounded-xl text-sm font-semibold hover:bg-red-600 shadow-md shadow-red-200">Xóa</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
