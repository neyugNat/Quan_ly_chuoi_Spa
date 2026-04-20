# Phân Tích Chi Tiết - Hệ Thống Quản Lý Chuỗi Spa

**Ngày phân tích:** April 20, 2026  
**Phiên bản:** MVP (Minimum Viable Product)

---

## I. TỔNG QUAN DỰ ÁN

### 1.1 Mô Tả
**Hệ thống quản lý vận hành chuỗi spa** - Ứng dụng web quản lý toàn hoàn chuỗi spa với tập trung vào:
- Quản lý đa chi nhánh (multi-tenant)
- Quản lý nhân sự, lịch trình làm việc
- Quản lý dịch vụ và lịch hẹn khách hàng
- Quản lý hóa đơn và thanh toán
- Quản lý kho hàng
- Báo cáo doanh thu

### 1.2 Kiến Trúc
- **Frontend:** Jinja2 templates + CSS thuần (Server-rendered)
- **Backend:** Python 3.10+ + Flask 3
- **Database:** SQLite (spa_mvp.db)
- **ORM:** Flask-SQLAlchemy
- **Authentication:** Session-based (không JWT)

### 1.3 Mục Tiêu Chính
✅ Quản lý vận hành chi nhánh tập trung  
✅ Tối ưu hóa quy trình đặt lịch hẹn  
✅ Theo dõi doanh thu và hóa đơn  
✅ Quản lý kho hàng giữa chi nhánh  
✅ Phân quyền rõ ràng theo vai trò

---

## II. CÔNG NGHỆ KỸ THUẬT

### 2.1 Stack Công Nghệ
| Thành phần | Công nghệ | Phiên bản |
|-----------|----------|---------|
| Backend | Python + Flask | 3.10+ |
| Database | SQLite | 3.x |
| ORM | SQLAlchemy | 2.x |
| Web Framework | Flask | 3.x |
| Template | Jinja2 | 3.x |
| Security | Werkzeug (hash) | 2.x |

### 2.2 Dependencies Chính
```
Flask==3.x
Flask-SQLAlchemy==3.x
Werkzeug==2.x
click==8.x (CLI)
```

### 2.3 Cấu Trúc Thư Mục
```
Quan_ly_chuoi_Spa/
├── backend/
│   ├── app.py                 # App factory + CLI commands
│   ├── web.py                 # Blueprint, auth, helpers chung
│   ├── config.py              # Cấu hình (SECRET_KEY, DATABASE_URL)
│   ├── extensions.py          # SQLAlchemy setup
│   ├── models.py              # Tất cả entities + migrations
│   ├── logs.py                # Activity logging
│   ├── requirements.txt        # Dependencies
│   ├── templates/web/         # HTML templates
│   ├── static/style.css       # CSS chung
│   └── web_modules/           # Business logic modules
│       ├── xac_thuc.py        # Authentication
│       ├── tong_quan.py       # Dashboard
│       ├── tai_khoan.py       # Account management
│       ├── chi_nhanh.py       # Branch management
│       ├── nhan_su.py         # Staff management
│       ├── dich_vu.py         # Service management
│       ├── lich_hen.py        # Appointment management
│       ├── hoa_don.py         # Invoice management
│       ├── kho.py             # Inventory management
│       ├── nhat_ky.py         # Activity logs
│       └── bao_cao.py         # Reports
├── instance/
│   └── spa_mvp.db             # SQLite database runtime
├── start_dev.ps1              # PowerShell dev script
└── README.md                  # Documentation
```

---

## III. TỪ VỰC (ENTITIES) - MÔ HÌNH DỮ LIỆU

### 3.1 Danh Sách Entities Chính

#### **Branch (Chi Nhánh)**
```python
- id (PK)
- branch_code: VARCHAR(16) - Mã chi nhánh (VD: CN001)
- name: VARCHAR(255) - Tên chi nhánh (UNIQUE)
- address: VARCHAR(500) - Địa chỉ
- phone: VARCHAR(32) - Số điện thoại (UNIQUE)
- manager_staff_id: FK(Staff) - Quản lý chi nhánh
- status: VARCHAR(32) - active|inactive
- created_at: DATETIME
```

#### **User (Tài Khoản Đăng Nhập)**
```python
- id (PK)
- username: VARCHAR(64) - Tên đăng nhập (UNIQUE)
- password_hash: VARCHAR(255) - Hash bcrypt/scrypt
- role: VARCHAR(32) - super_admin|branch_manager|receptionist|inventory_controller|technician
- branch_id: FK(Branch) - Chi nhánh quản lý
- staff_id: FK(Staff) - Gắn kết với nhân sự (optional)
- is_active: BOOLEAN
- created_at: DATETIME
```

#### **Staff (Nhân Sự)**
```python
- id (PK)
- branch_id: FK(Branch) - Chi nhánh (FK)
- full_name: VARCHAR(255) - Họ tên
- phone: VARCHAR(32) - SĐT (UNIQUE)
- title: VARCHAR(64) - Chức vụ (VD: Kỹ thuật viên, Lễ tân)
- status: VARCHAR(32) - active|inactive
- start_date: DATE - Ngày bắt đầu làm việc
- created_at: DATETIME
Constraints: (branch_id, phone) UNIQUE
```

#### **StaffShift (Lịch Làm Việc)**
```python
- id (PK)
- branch_id: FK(Branch)
- staff_id: FK(Staff)
- weekday: INT - 0:Thứ Hai ... 6:Chủ Nhật
- start_time: VARCHAR(5) - "08:00"
- end_time: VARCHAR(5) - "21:00"
- status: VARCHAR(32) - active|inactive
- created_at: DATETIME
Constraints: (staff_id, weekday) UNIQUE
```

#### **Customer (Khách Hàng)**
```python
- id (PK)
- branch_id: FK(Branch)
- full_name: VARCHAR(255)
- phone: VARCHAR(32)
- segment: VARCHAR(32) - regular|vip (phân khúc)
- note: VARCHAR(500)
- visit_count: INT - Số lần ghé thăm
- total_spent: DECIMAL(12,2) - Tổng chi tiêu
- last_visit_at: DATETIME - Lần cuối ghé thăm
- created_at: DATETIME
Constraints: (branch_id, phone) UNIQUE
```

#### **Service (Dịch Vụ)**
```python
- id (PK)
- branch_id: FK(Branch)
- name: VARCHAR(255) - Tên dịch vụ
- group_name: VARCHAR(64) - Nhóm (VD: Massage, Chăm sóc da)
- price: DECIMAL(12,2) - Giá dịch vụ
- duration_minutes: INT - Thời lượng (phút)
- status: VARCHAR(32) - active|inactive
- created_at: DATETIME
```

#### **ServiceInventoryUsage (Sử Dụng Hàng Hóa cho Dịch Vụ)**
```python
- id (PK)
- service_id: FK(Service)
- item_id: FK(InventoryItem)
- quantity: DECIMAL(12,2) - Số lượng sử dụng
Constraints: (service_id, item_id) UNIQUE
```

#### **Room (Phòng Làm Việc)**
```python
- id (PK)
- branch_id: FK(Branch)
- name: VARCHAR(64) - Tên phòng (VD: Phòng 1, VIP)
- room_type: VARCHAR(64) - Loại phòng
- status: VARCHAR(32) - active|inactive
- created_at: DATETIME
Constraints: (branch_id, name) UNIQUE
```

#### **Appointment (Lịch Hẹn)**
```python
- id (PK)
- branch_id: FK(Branch)
- customer_id: FK(Customer) - nullable
- customer_name: VARCHAR(255) - Tên khách (backup nếu không ghi khách)
- customer_phone: VARCHAR(32)
- room_id: FK(Room) - nullable
- service_id: FK(Service)
- technician_id: FK(Staff) - Nhân viên thực hiện
- appointment_date: DATE
- appointment_time: VARCHAR(5) - "HH:MM"
- end_time: VARCHAR(5) - nullable
- status: VARCHAR(16) - pending|completed|cancelled|overdue
- note: VARCHAR(500)
- created_by: VARCHAR(64) - Username người tạo
- created_at: DATETIME
Relationships:
  - service_items: [AppointmentServiceItem] (1-N)
  - invoice: Invoice (1-1, nullable)
```

#### **AppointmentServiceItem (Chi Tiết Dịch Vụ của Lịch Hẹn)**
```python
- id (PK)
- appointment_id: FK(Appointment)
- service_id: FK(Service)
- service_name: VARCHAR(255)
Constraints: (appointment_id, service_id) UNIQUE
```

#### **Supplier (Nhà Cung Cấp)**
```python
- id (PK)
- name: VARCHAR(255) - Tên nhà cung cấp (UNIQUE)
- phone: VARCHAR(32)
- address: VARCHAR(500)
- status: VARCHAR(32) - active|inactive
- created_at: DATETIME
```

#### **InventoryItem (Loại Hàng Hóa)**
```python
- id (PK)
- name: VARCHAR(255) - Tên hàng (UNIQUE)
- unit: VARCHAR(32) - Đơn vị (hộp, chai, gói)
- group_name: VARCHAR(64) - Nhóm (VD: Mỹ phẩm, Dụng cụ)
- min_stock: DECIMAL(12,2) - Tồn kho tối thiểu (cảnh báo)
- status: VARCHAR(32) - active|inactive
- created_at: DATETIME
```

#### **InventoryStock (Tồn Kho Theo Chi Nhánh)**
```python
- id (PK)
- branch_id: FK(Branch)
- item_id: FK(InventoryItem)
- quantity: DECIMAL(12,2) - Số lượng tồn
- created_at: DATETIME
Constraints: (branch_id, item_id) UNIQUE
```

#### **InventoryLot (Lô Hàng - Theo Dõi Hạn Sử Dụng)**
```python
- id (PK)
- branch_id: FK(Branch)
- item_id: FK(InventoryItem)
- supplier_id: FK(Supplier) - nullable
- lot_code: VARCHAR(64) - Mã lô
- expiry_date: DATE - Hạn sử dụng
- quantity: DECIMAL(12,2) - Số lượng của lô
- created_at: DATETIME
Constraints: (branch_id, item_id, lot_code) UNIQUE
```

#### **InventoryTransfer (Chuyển Hàng Giữa Chi Nhánh)**
```python
- id (PK)
- from_branch_id: FK(Branch) - Chi nhánh gửi
- to_branch_id: FK(Branch) - Chi nhánh nhận
- item_id: FK(InventoryItem)
- quantity: DECIMAL(12,2) - Số lượng
- note: VARCHAR(500)
- status: VARCHAR(32) - completed|pending
- created_at: DATETIME
```

#### **InventoryTransaction (Giao Dịch Kho - Nhập/Xuất/Chuyển)**
```python
- id (PK)
- branch_id: FK(Branch)
- item_id: FK(InventoryItem)
- type: VARCHAR(16) - purchase|usage|transfer|adjustment
- related_invoice_id: FK(Invoice) - nullable
- supplier_id: FK(Supplier) - nullable
- source_branch_id, target_branch_id: FK(Branch) - nullable
- quantity: DECIMAL(12,2) - Số lượng thay đổi
- lot_code: VARCHAR(64)
- expiry_date: DATE
- supplier_name: VARCHAR(255)
- note: VARCHAR(500)
- created_at: DATETIME
```

#### **Invoice (Hóa Đơn)**
```python
- id (PK)
- code: VARCHAR(32) - Mã hóa đơn (UNIQUE)
- branch_id: FK(Branch)
- staff_id: FK(Staff) - Nhân viên lập
- customer_id: FK(Customer) - nullable
- appointment_id: FK(Appointment) - nullable (UNIQUE)
- customer_name, customer_phone: VARCHAR
- subtotal_amount: DECIMAL(12,2) - Tiền hàng
- discount_amount: DECIMAL(12,2) - Chiết khấu
- tax_amount: DECIMAL(12,2) - Thuế
- total_amount: DECIMAL(12,2) - Tổng cộng
- paid_amount: DECIMAL(12,2) - Đã thanh toán
- balance_amount: DECIMAL(12,2) - Còn nợ
- refund_amount: DECIMAL(12,2) - Hoàn tiền
- status: VARCHAR(32) - paid|partial|unpaid|refunded|canceled
- payment_status: VARCHAR(32) - paid|partial|unpaid
- payment_method: VARCHAR(32) - cash|card|transfer
- note: VARCHAR(500)
- canceled_reason, canceled_at: nullable
- inventory_consumed_at: DATETIME - Khi nào hàng được tiêu thụ
- last_action_by: VARCHAR(64)
- created_at: DATETIME
Relationships:
  - items: [InvoiceItem] (1-N)
  - payments: [InvoicePayment] (1-N)
```

#### **InvoiceItem (Chi Tiết Dòng Hóa Đơn)**
```python
- id (PK)
- invoice_id: FK(Invoice)
- service_id: FK(Service) - nullable
- service_name: VARCHAR(255)
- qty: DECIMAL(12,2) - Số lượng
- unit_price: DECIMAL(12,2) - Giá đơn vị
- line_total: DECIMAL(12,2) - Tổng dòng (qty * unit_price)
```

#### **InvoicePayment (Thanh Toán Hóa Đơn)**
```python
- id (PK)
- invoice_id: FK(Invoice)
- payment_type: VARCHAR(16) - payment|refund
- method: VARCHAR(32) - cash|card|transfer
- amount: DECIMAL(12,2) - Số tiền thanh toán
- note: VARCHAR(500)
- created_at: DATETIME
- created_by: VARCHAR(64)
```

#### **ActivityLog (Nhật Ký Hoạt Động)**
```python
- id (PK)
- created_at: DATETIME - Khi tạo
- action: VARCHAR(64) - create_account, create_branch, etc. (INDEX)
- action_label: VARCHAR(128) - Mô tả hành động
- branch_id: FK(Branch) - nullable
- actor_user_id: FK(User) - Người thực hiện
- actor_username: VARCHAR(64)
- actor_role: VARCHAR(32)
- entity_type: VARCHAR(64) - appointment, invoice, etc.
- entity_id: INT (INDEX)
- message: VARCHAR(500) - Chi tiết
- details_json: TEXT - JSON thêm
```

### 3.2 Mối Quan Hệ Chính
```
Branch (1) ──→ (N) Staff
         └──→ (N) Customer
         └──→ (N) Service
         └──→ (N) Room
         └──→ (N) Appointment
         └──→ (N) Invoice
         └──→ (N) InventoryStock
         └──→ (N) ActivityLog

User (N) ──→ (1) Branch
      └──→ (1) Staff

Appointment (1) ──→ (1) Invoice
           └──→ (N) AppointmentServiceItem

Invoice (1) ──→ (N) InvoiceItem
       └──→ (N) InvoicePayment
```

---

## IV. THIẾT KẾ CẤP ĐỘ QUYỀN (PERMISSION MATRIX)

### 4.1 Các Vai Trò (Roles)

| Vai Trò | Mã | Mô Tả | Phạm Vi |
|---------|-----|-------|--------|
| **Super Admin** | `super_admin` | Quản trị viên hệ thống | Toàn chuỗi |
| **Branch Manager** | `branch_manager` | Quản lý chi nhánh | Chi nhánh được gán |
| **Receptionist** | `receptionist` | Lễ tân đặt lịch | Chi nhánh được gán |
| **Inventory Controller** | `inventory_controller` | Quản lý kho | Chi nhánh được gán |
| **Technician** | `technician` | Kỹ thuật viên | Chi nhánh được gán (xem lịch hẹn) |

### 4.2 Ma Trận Quyền Chi Tiết

#### **TRANG CHÍNH (Dashboard)**
```
Route: /web/dashboard
┌─────────────────────────────────────────────────────────────┐
│ Role               │ Quyền                                    │
├────────────────────┼──────────────────────────────────────────┤
│ super_admin        │ ✅ Xem toàn chuỗi + một chi nhánh cụ thể  │
│                    │ ✅ KPIs: Doanh thu, Số lịch, Kho thấp     │
│ branch_manager     │ ✅ Xem chi nhánh riêng                    │
│                    │ ✅ KPIs: Doanh thu, lịch hẹn hôm nay      │
│ receptionist       │ ❌ Điều hướng sang Appointments           │
│ inventory_ctrl     │ ❌ Điều hướng sang Inventory              │
│ technician         │ ❌ Điều hướng sang Appointments           │
└────────────────────┴──────────────────────────────────────────┘
```

#### **CHI NHÁNH (Branches)**
```
Route: /web/branches
┌─────────────────────────────────────────────────────────────┐
│ super_admin        │ ✅ Xem tất cả chi nhánh                   │
│                    │ ✅ CRUD chi nhánh                        │
│                    │ ✅ Gán quản lý & thay đổi trạng thái      │
├────────────────────┼──────────────────────────────────────────┤
│ branch_manager     │ ✅ Xem chi nhánh riêng                    │
│                    │ ✅ Cập nhật thông tin chi nhánh           │
│                    │ ❌ Không xóa, không gán quản lý           │
├────────────────────┼──────────────────────────────────────────┤
│ receptionist       │ ❌ Không truy cập                         │
│ inventory_ctrl     │ ❌ Không truy cập                         │
│ technician         │ ❌ Không truy cập                         │
└────────────────────┴──────────────────────────────────────────┘
```

#### **NHÂN SỰ (Staff)**
```
Route: /web/staff
┌─────────────────────────────────────────────────────────────┐
│ super_admin        │ ✅ Xem nhân sự tất cả chi nhánh           │
│                    │ ✅ CRUD nhân sự (Create, Read, Update)    │
│                    │ ✅ Quản lý lịch shift                     │
│                    │ ✅ Kích hoạt/Vô hiệu hóa                  │
├────────────────────┼──────────────────────────────────────────┤
│ branch_manager     │ ✅ Xem nhân sự chi nhánh riêng            │
│                    │ ✅ CRUD nhân sự chi nhánh                 │
│                    │ ✅ Quản lý lịch shift                     │
├────────────────────┼──────────────────────────────────────────┤
│ receptionist       │ ❌ Không truy cập                         │
│ inventory_ctrl     │ ❌ Không truy cập                         │
│ technician         │ ❌ Không truy cập                         │
└────────────────────┴──────────────────────────────────────────┘
```

#### **DỊCH VỤ (Services)**
```
Route: /web/services
┌─────────────────────────────────────────────────────────────┐
│ super_admin        │ ✅ CRUD dịch vụ toàn chuỗi                │
│                    │ ✅ Gán hàng hóa sử dụng cho dịch vụ       │
├────────────────────┼──────────────────────────────────────────┤
│ branch_manager     │ ✅ CRUD dịch vụ chi nhánh                 │
│                    │ ✅ Gán hàng hóa sử dụng                   │
├────────────────────┼──────────────────────────────────────────┤
│ receptionist       │ ✅ Xem dịch vụ (dùng khi đặt lịch)         │
│                    │ ❌ Không CRUD                             │
│ inventory_ctrl     │ ❌ Không truy cập                         │
│ technician         │ ❌ Không truy cập                         │
└────────────────────┴──────────────────────────────────────────┘
```

#### **LỊCH HẸN (Appointments)**
```
Route: /web/appointments
┌─────────────────────────────────────────────────────────────┐
│ super_admin        │ ✅ Xem các lịch hẹn toàn chuỗi            │
│                    │ ✅ CRUD lịch hẹn                          │
│                    │ ✅ Đánh dấu hoàn thành/Hủy                │
├────────────────────┼──────────────────────────────────────────┤
│ branch_manager     │ ✅ Xem các lịch chi nhánh                 │
│                    │ ✅ CRUD lịch                              │
│                    │ ✅ Đánh dấu hoàn thành/Hủy                │
├────────────────────┼──────────────────────────────────────────┤
│ receptionist       │ ✅ CRUD lịch hẹn (đặt, sửa, hủy)          │
│                    │ ✅ Xem danh sách lịch hôm nay             │
│                    │ ✅ Tìm kiếm theo khách, ngày              │
├────────────────────┼──────────────────────────────────────────┤
│ technician         │ ✅ Xem lịch hẹn của họ                    │
│                    │ ❌ Không CRUD lịch                        │
├────────────────────┼──────────────────────────────────────────┤
│ inventory_ctrl     │ ❌ Không truy cập                         │
└────────────────────┴──────────────────────────────────────────┘
```

#### **HÓA ĐƠN (Invoices)**
```
Route: /web/invoices
┌─────────────────────────────────────────────────────────────┐
│ super_admin        │ ✅ Xem tất cả hóa đơn                     │
│                    │ ✅ CRUD hóa đơn                           │
│                    │ ✅ Xử lý thanh toán/Hoàn tiền             │
│                    │ ✅ Hủy hóa đơn                            │
├────────────────────┼──────────────────────────────────────────┤
│ branch_manager     │ ✅ Xem hóa đơn chi nhánh                  │
│                    │ ✅ CRUD hóa đơn chi nhánh                 │
│                    │ ✅ Xử lý thanh toán/Hoàn tiền             │
│                    │ ✅ Hủy hóa đơn                            │
├────────────────────┼──────────────────────────────────────────┤
│ receptionist       │ ✅ Xem & Cập nhật hóa đơn                 │
│                    │ ✅ Ghi nhận thanh toán                    │
│                    │ ✅ Tìm kiếm hóa đơn                       │
│ inventory_ctrl     │ ❌ Không truy cập                         │
│ technician         │ ❌ Không truy cập                         │
└────────────────────┴──────────────────────────────────────────┘
```

#### **KHO HÀNG (Inventory)**
```
Route: /web/inventory
┌─────────────────────────────────────────────────────────────┐
│ super_admin        │ ✅ Xem, Nhập, Chuyển hàng                 │
│                    │ ✅ Quản lý lô hàng (theo dõi hạn)         │
│                    │ ✅ Cấu hình hàng hóa                      │
├────────────────────┼──────────────────────────────────────────┤
│ branch_manager     │ ✅ Xem, Nhập, Chuyển hàng chi nhánh       │
│                    │ ✅ Quản lý lô hàng                        │
│                    │ ✅ Cấu hình hàng hóa                      │
├────────────────────┼──────────────────────────────────────────┤
│ inventory_ctrl     │ ✅ Xem, Nhập, Chuyển hàng                 │
│                    │ ✅ Quản lý lô hàng, điều chỉnh tồn kho    │
│                    │ ❌ Không cấu hình hàng hóa bổ sung         │
├────────────────────┼──────────────────────────────────────────┤
│ receptionist       │ ❌ Không truy cập                         │
│ technician         │ ❌ Không truy cập                         │
└────────────────────┴──────────────────────────────────────────┘
```

#### **TÍNH ĐỦ QUYỀN (Accounts)**
```
Route: /web/accounts
┌─────────────────────────────────────────────────────────────┐
│ super_admin        │ ✅ CRUD tài khoản cho tất cả vai trò      │
│                    │ ✅ Gán vai trò, gắn nhân sự              │
│                    │ ✅ Kích hoạt/Vô hiệu hóa tài khoản        │
│                    │ ✅ Thay đổi mật khẩu                      │
├────────────────────┼──────────────────────────────────────────┤
│ branch_manager     │ ❌ Không truy cập                         │
│ receptionist       │ ❌ Không truy cập                         │
│ inventory_ctrl     │ ❌ Không truy cập                         │
│ technician         │ ❌ Không truy cập                         │
└────────────────────┴──────────────────────────────────────────┘
```

#### **BÁO CÁO (Reports)**
```
Route: /web/reports
┌─────────────────────────────────────────────────────────────┐
│ super_admin        │ ✅ Xem báo cáo toàn chuỗi                 │
│                    │ ✅ Lọc theo chi nhánh, khoảng thời gian   │
│                    │ ✅ Xuất CSV                               │
├────────────────────┼──────────────────────────────────────────┤
│ branch_manager     │ ✅ Xem báo cáo chi nhánh                  │
│                    │ ✅ Xuất báo cáo                           │
├────────────────────┼──────────────────────────────────────────┤
│ receptionist       │ ❌ Không truy cập                         │
│ inventory_ctrl     │ ❌ Không truy cập                         │
│ technician         │ ❌ Không truy cập                         │
└────────────────────┴──────────────────────────────────────────┘
```

#### **NHẬT KÝ HOẠT ĐỘNG (Activity Logs)**
```
Route: /web/activity_logs
┌─────────────────────────────────────────────────────────────┐
│ super_admin        │ ✅ Xem nhật ký toàn chuỗi                 │
│                    │ ✅ Lọc theo tác nhân, hành động, chi nhánh│
├────────────────────┼──────────────────────────────────────────┤
│ branch_manager     │ ✅ Xem nhật ký chi nhánh                  │
│                    │ ✅ Lọc theo hành động                     │
├────────────────────┼──────────────────────────────────────────┤
│ receptionist       │ ❌ Không truy cập                         │
│ inventory_ctrl     │ ❌ Không truy cập                         │
│ technician         │ ❌ Không truy cập                         │
└────────────────────┴──────────────────────────────────────────┘
```

### 4.3 Quy Tắc Truy Cập (Access Control Rules)

#### **Decorator `@roles_required()`**
Bảo vệ các route, chỉ cho phép vai trò cụ thể:
```python
@web_bp.get("/accounts")
@roles_required("super_admin")
def accounts():
    # Chỉ super_admin có thể truy cập
    ...
```

#### **Quy Tắc Phạm Vi (Scope Rules)**
```
┌─────────────────────┬──────────────────────────────────────┐
│ Role                │ Phạm vi dữ liệu                       │
├─────────────────────┼──────────────────────────────────────┤
│ super_admin         │ Tất cả chi nhánh (scope_branch_ids=[]) │
│ branch_manager      │ Chi nhánh được gán (user.branch_id)  │
│ receptionist        │ Chi nhánh được gán                   │
│ inventory_ctrl      │ Chi nhánh được gán                   │
│ technician          │ Chi nhánh được gán (chỉ xem)         │
└─────────────────────┴──────────────────────────────────────┘
```

#### **Kiểm Tra Giữa Quá Trình (Runtime Checks)**
```python
# 1. Kiểm tra branch_id có trong phạm vi của user
scope_ids = get_current_branch_scope()
if branch_id not in scope_ids:
    return "Không có quyền truy cập chi nhánh này"

# 2. Kiểm tra entity có thuộc chi nhánh được phép
customer = Customer.query.get(customer_id)
if customer.branch_id not in scope_ids:
    return "Không có quyền truy cập dữ liệu này"

# 3. Kiểm tra vai trò phù hợp với nhân sự
if not is_staff_compatible_with_role(staff, role):
    return "Nhân sự không phù hợp với vai trò"
```

### 4.4 Chính Sách Mật Khẩu & Bảo Mật

```python
# Độ dài tối thiểu
MIN_PASSWORD_LENGTH = 6

# Hashing (từ Werkzeug)
- scrypt (mặc định)
- pbkdf2 (fallback)
- argon2 (hỗ trợ)

# Kiểm tra mật khẩu cũ
is_password_hash(value) -> Bool  # Kiểm tra xem đã hash chưa
password_needs_rehash -> Property  # Có cần hash lại không

# Tạo & Xác thực
user.set_password(raw_password)  # Hash mật khẩu
user.verify_password(raw_password)  # Xác thực
```

---

## V. CÁC MODULE NGHIỆP VỤ (BUSINESS LOGIC MODULES)

### 5.1 MODULE XÁC THỰC (xac_thuc.py)

**Mục đích:** Quản lý đăng nhập/đăng xuất, session, xác thực người dùng

**Endpoints:**
```
GET  /web/login              - Form đăng nhập
POST /web/login              - Xử lý đăng nhập
GET  /web/logout             - Đăng xuất
POST /web/session-remaining  - AJAX: thời gian session còn lại
```

**Quy Trình Đăng Nhập:**
1. Người dùng nhập username + password
2. Tìm User theo username
3. Verify password với password_hash
4. Nếu đúng → Tạo session, lưu user_id, role
5. Nếu sai → Flash lỗi "Username hoặc mật khẩu sai"

**Dữ Liệu Session:**
```python
session = {
    'user_id': user.id,
    'username': user.username,
    'role': user.role,
    'branch_id': user.branch_id,  # Chi nhánh chính của user
    'staff_id': user.staff_id,     # Nếu có
}
```

**Helpers:**
```python
get_current_user()              # Lấy User từ session
require_login(view)             # Decorator bắt buộc đăng nhập
roles_required(*roles)          # Decorator kiểm tra vai trò
get_current_branch_scope()      # Lấy danh sách chi nhánh được phép
```

---

### 5.2 MODULE TỔNG QUAN (tong_quan.py)

**Mục đích:** Dashboard tổng hợp KPI chính, biểu đồ doanh thu

**Endpoint:**
```
GET /web/dashboard
```

**Chức Năng:**
```
1. KPI Chính
   ├─ Số chi nhánh hoạt động
   ├─ Số nhân sự
   ├─ Số dịch vụ
   └─ Số mặt hàng tồn kho thấp

2. Doanh Thu
   ├─ Doanh thu hôm nay
   ├─ Doanh thu tháng này
   ├─ Chi nhánh doanh thu cao nhất
   └─ Chi nhánh doanh thu thấp nhất

3. Danh Sách
   ├─ 6 hóa đơn mới nhất
   └─ 8 mặt hàng tồn kho thấp nhất
```

**Quy Tắc Dữ Liệu:**
- Super Admin: Có thể xem toàn chuỗi hoặc 1 chi nhánh cụ thể
- Branch Manager: Chỉ xem chi nhánh riêng

---

### 5.3 MODULE TÀI KHOẢN (tai_khoan.py)

**Mục đích:** Quản lý tài khoản người dùng, phân quyền theo vai trò

**Endpoints:**
```
GET  /web/accounts                    - Danh sách tài khoản
POST /web/accounts/save               - Thêm/Sửa tài khoản
POST /web/accounts/toggle-status      - Bật/Tắt tài khoản
POST /web/accounts/reset-password     - Đặt lại mật khẩu
DELETE /web/accounts/<user_id>        - Xóa tài khoản
```

**Các Vai Trò Có Thể Tạo:**
```
- branch_manager    (Quản lý chi nhánh)
- receptionist      (Lễ tân)
- inventory_controller (Kiểm soát kho)
- technician        (Kỹ thuật viên)
```

**Quy Tắc Tạo Tài Khoản:**
1. Username bắt buộc (unique)
2. Vai trò bắt buộc (trong ACCOUNT_MANAGED_ROLES)
3. Chi nhánh bắt buộc
4. Phải gắn với nhân sự hoạt động
5. Nhân sự phải phù hợp với vai trò (kiểm tra chức vụ)
6. 1 nhân sự chỉ có 1 tài khoản (không trùng lặp)
7. Mật khẩu tối thiểu 6 ký tự (nếu có)

**Kiểm Tra Chức Vụ:**
```python
ROLE_STAFF_TITLES = {
    'branch_manager': {'quản lý chi nhánh', 'quan ly chi nhanh', ...},
    'receptionist': {'lễ tân', 'le tan'},
    'inventory_controller': {'kiểm soát kho', 'kiem soat kho'},
    'technician': {'kỹ thuật viên', 'ky thuat vien'},
}
```

---

### 5.4 MODULE CHI NHÁNH (chi_nhanh.py)

**Mục đích:** Quản lý thông tin chi nhánh, quản lý viên, trạng thái

**Endpoints:**
```
GET  /web/branches            - Danh sách chi nhánh
POST /web/branches/save       - Thêm/Sửa chi nhánh
DELETE /web/branches/<id>     - Xóa chi nhánh
POST /web/branches/toggle     - Bật/Tắt trạng thái
```

**Thông Tin Chi Nhánh:**
```
- Mã chi nhánh (ví: CN001, CN002) - UNIQUE
- Tên chi nhánh - UNIQUE
- Địa chỉ
- Số điện thoại - UNIQUE
- Quản lý (từ danh sách Staff)
- Trạng thái (active/inactive)
```

**Quy Tắc Xóa Chi Nhánh:**
```
Chi nhánh chỉ có thể xóa nếu:
✅ Chưa có nhân sự
✅ Chưa có hóa đơn
✅ Chưa có lịch hẹn
✅ Chưa có dịch vụ
✅ Chưa có tồn kho
✅ Chưa có giao dịch kho

Nếu có → Lỗi: "Chi nhánh đang sử dụng, không thể xóa"
```

---

### 5.5 MODULE NHÂN SỰ (nhan_su.py)

**Mục đích:** Quản lý thông tin nhân viên, chức vụ, lịch làm việc

**Endpoints:**
```
GET  /web/staff            - Danh sách nhân sự
POST /web/staff/save       - Thêm/Sửa nhân sự
DELETE /web/staff/<id>     - Xóa nhân sự
GET  /web/staffshifts      - Quản lý lịch làm việc
POST /web/staffshifts/save - Lưu lịch làm việc
```

**Thông Tin Nhân Sự:**
```
- Họ tên
- Số điện thoại (UNIQUE) - 8-15 chữ số
- Chức vụ (danh sách mặc định)
- Ngày bắt đầu
- Trạng thái (active/inactive)
```

**Chức Vụ Mặc Định:**
```
- Quản lý chi nhánh
- Lễ tân
- Kỹ thuật viên
- Kiểm soát kho
```

**Lịch Làm Việc (StaffShift):**
```
- Tuần: Thứ 2 (0) - Chủ Nhật (6)
- Giờ bắt đầu: hh:mm (VD: 08:00)
- Giờ kết thúc: hh:mm (VD: 21:00)
- Trạng thái: active/inactive
- Constraint: (staff_id, weekday) unique
```

---

### 5.6 MODULE DỊCH VỤ (dich_vu.py)

**Mục đích:** Quản lý danh sách dịch vụ, giá, thời lượng

**Endpoints:**
```
GET  /web/services            - Danh sách dịch vụ
POST /web/services/save       - Thêm/Sửa dịch vụ
DELETE /web/services/<id>     - Xóa dịch vụ
GET  /web/services/inventory  - Gán hàng hóa cho dịch vụ
POST /web/services/inventory/save
```

**Thông Tin Dịch Vụ:**
```
- Tên dịch vụ
- Nhóm dịch vụ (VD: Massage, Chăm sóc da)
- Giá dịch vụ (VD: 150.000)
- Thời lượng (phút, VD: 60)
- Trạng thái (active/inactive)
- Chi nhánh
```

**Gán Hàng Hóa cho Dịch Vụ:**
```
Mỗi dịch vụ có thể sử dụng nhiều hàng hóa:
Service (1) ──→ (N) ServiceInventoryUsage
                    └──→ (1) InventoryItem + Số lượng
```

---

### 5.7 MODULE LỊCH HẸN (lich_hen.py)

**Mục đích:** Quản lý đặt lịch hẹn khách hàng, xác nhận, hủy

**Endpoints:**
```
GET  /web/appointments                   - Danh sách lịch hẹn
POST /web/appointments/create            - Thêm lịch hẹn
POST /web/appointments/save              - Cập nhật lịch
POST /web/appointments/<id>/complete     - Đánh dấu hoàn thành
POST /web/appointments/<id>/cancel       - Hủy lịch
```

**Thông Tin Lịch Hẹn:**
```
- Khách hàng (ghi tên + SĐT, có thể ko có record)
- Dịch vụ (1 hoặc nhiều)
- Phòng (optional)
- Kỹ thuật viên (thực hiện)
- Ngày hẹn (DATE)
- Giờ hẹn (HH:MM)
- Trạng thái: pending|completed|cancelled|overdue
- Ghi chú
```

**Quy Tắc Tạo Lịch:**
1. Khách hàng: Ghi tên + SĐT (không bắt buộc có record)
2. Dịch vụ: Bắt buộc (1 hoặc nhiều)
3. Kỹ thuật viên: Phải là nhân sự với chức vụ "Kỹ thuật viên"
4. Ngày/Giờ: Không thể trong quá khứ
5. Phòng: Không xung đột với lịch khác

**Kiểm Tra Xung Đột Phòng:**
```python
# Nếu chọn phòng, kiểm tra phòng có sẵn vào thời gian đó
existing = Appointment.query.filter(
    Appointment.room_id == room_id,
    Appointment.appointment_date == date,
    Appointment.appointment_time == time,
    Appointment.status != 'cancelled'
).first()
if existing:
    return "Phòng không sẵn"
```

**Tự Động Đánh Dấu Overdue:**
```python
# Lịch hẹn > 6 giờ trước đó và vẫn pending → overdue
if (now - appointment_time) > 6 hours and status == 'pending':
    status = 'overdue'
```

**Tích Hợp Khách Hàng:**
```python
# Khi tạo lịch, tự động cập nhật hoặc tạo Customer:
upsert_customer(
    branch_id=branch_id,
    phone=phone,
    full_name=name,
    visit_count+=1,
    last_visit_at=now()
)
```

---

### 5.8 MODULE HÓA ĐƠN (hoa_don.py)

**Mục đích:** Tạo, cập nhật, hủy hóa đơn; ghi nhận thanh toán; hoàn tiền

**Endpoints:**
```
GET  /web/invoices              - Danh sách hóa đơn
POST /web/invoices/create       - Tạo hóa đơn mới
POST /web/invoices/<id>/update  - Cập nhật chi tiết
POST /web/invoices/<id>/pay     - Ghi nhận thanh toán
POST /web/invoices/<id>/refund  - Hoàn tiền
POST /web/invoices/<id>/void    - Hủy hóa đơn
GET  /web/invoices/export       - Xuất CSV
```

**Thông Tin Hóa Đơn:**
```
- Mã hóa đơn (auto: INV-YYYYMMDD-XXXXX)
- Khách hàng (optional record + tên + SĐT)
- Chi nhánh
- Lịch hẹn (optional, 1-1)
- Nhân viên lập
- Ngày tạo
```

**Chi Tiết Hóa Đơn:**
```
Hóa Đơn (1) ──→ (N) InvoiceItem
         ├─ Dịch vụ
         ├─ Số lượng
         ├─ Giá đơn vị
         └─ Tính tổng = SUM(qty × unit_price)

         ──→ (N) InvoicePayment
             ├─ Loại: payment|refund
             ├─ Phương thức: cash|card|transfer
             ├─ Số tiền
             ├─ Ngày giờ
             └─ Người ghi nhận
```

**Tính Toán Số Tiền:**
```
Tiền Hàng (Subtotal) = SUM(item.qty × item.unit_price)
Tiền Lẻ (Discount)   = Nhập vào (≥ 0)
Thuế (Tax)           = Nhập vào (≥ 0)
─────────────────────────────────────────
Tổng Cộng (Total)    = Subtotal - Discount + Tax

Đã Thanh Toán (Paid) = SUM(payment.amount) - SUM(refund.amount)
Còn Nợ (Balance)     = Total - Paid
Hoàn Tiền (Refund)   = SUM(refund type payments)
```

**Trạng Thái Hóa Đơn:**
```
┌────────────────┬──────────────────────────────────────┐
│ Status         │ Điều kiện                            │
├────────────────┼──────────────────────────────────────┤
│ paid           │ Paid Amount ≥ Total Amount           │
│ partial        │ Paid Amount > 0 AND < Total          │
│ unpaid         │ Paid Amount = 0                      │
│ refunded       │ Refund Amount > 0                    │
│ canceled       │ Bị hủy (có lý do)                    │
└────────────────┴──────────────────────────────────────┘
```

**Quy Tắc Xóa/Hủy Hóa Đơn:**
```
1. Có thể hủy hóa đơn chưa paid đầy đủ
2. Khi hủy:
   - Hoàn lại hàng hóa đã tiêu thụ
   - Ghi lại lý do hủy + thời gian
   - Cập nhật trạng thái → canceled
3. Không thể sửa hóa đơn đã canceled
```

**Tiêu Thụ Hàng Hóa:**
```
trigger: Khi hóa đơn được thanh toán đầy đủ
action:
  ├─ Lấy danh sách ServiceInventoryUsage từ các service trong hóa đơn
  ├─ Trừ từ InventoryStock của chi nhánh
  ├─ Ghi InvoiceTransaction (type='usage')
  ├─ Cập nhật InventoryLot (FIFO)
  ├─ Đánh dấu inventory_consumed_at = now()
  └─ Nếu tồn kho < min_stock → cảnh báo
```

**Hoàn Lại Hàng Hóa:**
```
trigger: Khi hóa đơn bị hủy
action:
  ├─ Nếu inventory_consumed_at != null:
  │   ├─ Cộng lại vào InventoryStock
  │   ├─ Ghi InvoiceTransaction (type='reversal')
  │   └─ Ghi nhân AnctivityLog
  └─ Xóa InvoicePayment của hóa đơn
```

---

### 5.9 MODULE KHO HÀNG (kho.py)

**Mục đích:** Quản lý tồn kho, nhập/xuất, chuyển giữa chi nhánh, theo dõi hạn hộp

**Endpoints:**
```
GET  /web/inventory                      - Danh sách tồn kho
POST /web/inventory/stock/save           - Nhập/Sửa tồn kho
GET  /web/inventory/lots                 - Quản lý lô hàng
POST /web/inventory/lots/save            - Thêm/Sửa lô
POST /web/inventory/transfer             - Chuyển hàng giữa chi nhánh
GET  /web/inventory/transactions         - Lịch sử giao dịch
```

**Tồn Kho (InventoryStock):**
```
- Chi nhánh
- Loại hàng hóa
- Số lượng tồn
- Tồn kho tối thiểu (cảnh báo)
Constraint: (branch_id, item_id) unique
```

**Lô Hàng (InventoryLot):**
```
- Chi nhánh + Loại hàng + Mã lô (unique)
- Nhà cung cấp
- Hạn sử dụng
- Số lượng của lô
- Ngày tạo
→ Dùng FIFO khi xuất hàng
```

**Giao Dịch Kho (InventoryTransaction):**
```
Type:
  ├─ purchase  (Nhập từ nhà cung cấp)
  ├─ usage     (Tiêu thụ trong hóa đơn)
  ├─ transfer  (Chuyển chi nhánh khác)
  └─ adjustment (Điều chỉnh)

Ghi nhận:
  ├─ Chi nhánh
  ├─ Loại hàng
  ├─ Loại giao dịch + Lượng thay đổi
  ├─ Lô hàng + Hạn sử dụng
  ├─ Nhà cung cấp (nếu applicated)
  ├─ Chi nhánh nguồn/đích (nếu transfer)
  ├─ Liên liên invoice
  ├─ Ghi chú
  └─ Ngày giờ
```

**Chuyển Hàng (InventoryTransfer):**
```
- Chi nhánh gửi → Chi nhánh nhận
- Loại hàng + Số lượng
- Trạng thái: pending|completed
- Ghi chú (VD: thế chỗ lô hết hạn)
- Khi hoàn thành:
  ├─ Trừ khỏi chi nhánh gửi
  ├─ Cộng vào chi nhánh nhận
  ├─ Ghi InventoryTransaction (type='transfer')
  └─ Cập nhật InventoryLot
```

**Cảnh Báo Tồn Kho Thấp:**
```
if (InventoryStock.quantity <= InventoryItem.min_stock):
    ├─ Hiển thị cảnh báo trên dashboard
    ├─ Gợi ý nhập hàng
    └─ Liệt kê trong báo cáo
```

---

### 5.10 MODULE BÁAO CÁO (bao_cao.py)

**Mục đích:** Thống kê doanh thu, số lượng hóa đơn, chi nhánh

**Endpoints:**
```
GET /web/reports                  - Trang báo cáo
POST /web/reports/export          - Xuất CSV
```

**Báo Cáo:**
1. **Tổng Hợp Hóa Đơn**
   ```
   - Tổng giá trị hóa đơn (chưa hủy)
   - Số HĐ: ngàn, riêng phần, hủy
   - Doanh thu thu được
   - Nợ còn lại
   - Lọc: Khoảng ngày, chi nhánh
   ```

2. **Theo Trạng Thái**
   ```
   - Paid: số lượng, tổng tiền
   - Partial: số lượng, còn nợ
   - Unpaid: số lượng, nợ
   - Canceled: số lượng, giá trị hủy
   ```

3. **Doanh Thu Theo Chi Nhánh**
   ```
   - Chi nhánh (tên, mã)
   - Doanh thu tháng
   - Đơn hàng
   - Chiều hướng (so sánh với tháng trước)
   ```

4. **Hàng Hóa Sắp Hết Hạn**
   ```
   - Loại hàng, lô, hạn hộp
   - Chi nhánh
   - Cảnh báo: < 7 ngày hết hạn
   ```

---

### 5.11 MODULE NHẬT KÝ (nhat_ky.py)

**Mục đích:** Ghi nhận audit trail, theo dõi các hành động quan trọng

**Endpoints:**
```
GET /web/activity_logs      - Danh sách nhật ký
```

**Hành Động Ghi Nhận:**
```
- Tạo/Sửa/Xóa tài khoản
- Tạo/Sửa chi nhánh
- Tạo/Sửa/Hủy lịch hẹn
- Tạo/Thanh toán/Hủy hóa đơn
- Nhập/Xuất/Chuyển hàng
- Đăng nhập/Đăng xuất
```

**Thông Tin Ghi Nhận:**
```
ActivityLog:
  ├─ Thời gian
  ├─ Tác nhân (User ID, username, vai trò)
  ├─ Hành động (action code)
  ├─ Mô tả hành động (action_label)
  ├─ Entity (type: appointment, invoice, branch)
  ├─ Entity ID
  ├─ Chi nhánh liên quan
  ├─ Chi tiết JSON (trước/sau)
  └─ Thông điệp
```

---

## VI. LUỒNG XỬ LÝ (WORKFLOWS) - CÁC KỊCH BẢN CHÍNH

### 6.1 Luồng Đặt Lịch Hẹn (Appointment Flow)

```
┌─────────────────────────────────────────────────────────────┐
│ Bước 1: Lễ Tân Truy Cập Trang Đặt Lịch                     │
│ - GET /web/appointments                                    │
│ - Hiển thị danh sách lịch hôm nay + Form đặt lịch          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Bước 2: Nhập Thông Tin Khách & Dịch Vụ                    │
│ - Họ tên khách hàng (text)                                 │
│ - Số điện thoại (validate 8-15 chữ số)                     │
│ - Chọn 1 hoặc nhiều dịch vụ                                │
│ - Dự kiến thời gian công (từ duration_minutes)             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Bước 3: Chọn Kỹ Thuật Viên & Phòng                        │
│ - Danh sách kỹ thuật viên còn sẵn                          │
│ - Kiểm tra lịch shift của họ vào ngày/giờ                 │
│ - Chọn phòng (nếu có) - kiểm tra xung đột                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Bước 4: Xác Nhận & Lưu Lịch                               │
│ POST /web/appointments/create                              │
│ - Validate dữ liệu                                         │
│ - Tạo Appointment + AppointmentServiceItem                 │
│ - Tạo hoặc cập nhật Customer (upsert)                      │
│ - Ghi ActivityLog (create_appointment)                      │
│ - Flash: "Đặt lịch thành công"                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Luồng Hóa Đơn + Thanh Toán (Invoice Flow)

```
┌───────────────────────────────────────────────────────────┐
│ Cách 1: From Appointment (Tự động)                        │
│ - Khi lịch hẹn hoàn thành → Tạo Invoice trống             │
│ - Link 1-1 với Appointment                                │
│ - Pre-fill: service, khách hàng, kỹ thuật viên            │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ Bước 1: Tạo Hóa Đơn                                      │
│ POST /web/invoices/create                                │
│ - Chọn chi nhánh                                          │
│ - Chọn/Tạo khách hàng                                    │
│ - Kết nối lịch hẹn nếu có                                 │
│ - Gắn nhân viên (mặc định = logged-in staff)             │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ Bước 2: Thêm Chi Tiết Dịch Vụ                            │
│ POST /web/invoices/<id>/update                           │
│ - Thêm/Xóa dòng dịch vụ (InvoiceItem)                     │
│ - Nhập: Dịch vụ, số lượng, giá đơn vị                    │
│ - Hệ thống tự quay trong Subtotal                         │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ Bước 3: Tính Toán Tiền                                   │
│ - recalc_invoice():                                      │
│   ├─ Subtotal = SUM(qty × unit_price)                    │
│   ├─ Discount = User input (≥0)                          │
│   ├─ Tax = User input (≥0)                               │
│   └─ Total = Subtotal - Discount + Tax                   │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ Bước 4: Ghi Nhận Thanh Toán                              │
│ POST /web/invoices/<id>/pay                              │
│ - Chọn phương thức (cash, card, transfer)                │
│ - Nhập số tiền thanh toán                                │
│ - Có thể thanh toán nhiều lần (partial payment)          │
│ - Lưu InvoicePayment                                     │
│ - Cập nhật Payment Status + Balance                      │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ Bước 5: Tiêu Thụ Hàng Hóa (Auto)                        │
│ trigger: Paid Amount ≥ Total                             │
│ - Gọi consume_inventory_for_invoice()                    │
│ - Lấy ServiceInventoryUsage từ các service               │
│ - Trừ InventoryStock (Chi nhánh của HĐ)                 │
│ - Ghi InventoryTransaction (type='usage')                │
│ - Cập nhật InventoryLot (FIFO)                          │
│ - Đánh dấu inventory_consumed_at = now()                 │
└───────────────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────────────────────────────────┐
│ Bước 6: Cập Nhật Thống Kê Khách Hàng                    │
│ trigger: Hóa đơn thanh toán đầy đủ                       │
│ - sync_customer_stats():                                 │
│   ├─ visit_count += 1                                    │
│   ├─ total_spent += paid amount                          │
│   └─ last_visit_at = now()                               │
└───────────────────────────────────────────────────────────┘

Optional:
┌───────────────────────────────────────────────────────────┐
│ Hoàn Tiền / Hủy Hóa Đơn                                 │
│ POST /web/invoices/<id>/refund                           │
│ - Nhập số tiền hoàn                                      │
│ - Tạo InvoicePayment (type='refund')                     │
│ - Cập nhật Balance & Balance                             │
│                                                           │
│ POST /web/invoices/<id>/void                             │
│ - Kiểm tra status (không thể hủy đã hủy)                 │
│ - Nếu đã consumed → Hoàn lại hàng hóa                    │
│ - Ghi canceled_reason + canceled_at                      │
│ - Status → "canceled"                                    │
└───────────────────────────────────────────────────────────┘
```

### 6.3 Luồng Quản Lý Kho (Inventory Flow)

```
┌─────────────────────────────────────────────────────────────┐
│ Bước 1: Cấu Hình Hàng Hóa (Super Admin)                     │
│ - Tạo InventoryItem (toàn chuỗi)                           │
│ - Tên, đơn vị, nhóm, tồn kho tối thiểu                     │
│ - Liên kết dịch vụ dùng hàng (ServiceInventoryUsage)        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Bước 2: Nhập Hàng Mới                                       │
│ POST /web/inventory/lots/save                              │
│ - Chọn chi nhánh + loại hàng                              │
│ - Nhập: Mã lô, nhà cung cấp, hạn sử dụng, số lượng         │
│ - Tạo InventoryLot + InventoryStock                        │
│ - Ghi InventoryTransaction (type='purchase')               │
│ - Ghi ActivityLog                                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Bước 3: Theo Dõi Tồn Kho Thấp                              │
│ - Dashboard cảnh báo nếu quantity ≤ min_stock             │
│ - Báo cáo liệt kê những loại cần nhập                      │
│ - Gợi ý mua sắm                                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Bước 4: Chuyển Hàng Giữa Chi Nhánh                         │
│ POST /web/inventory/transfer                              │
│ - Chi nhánh gửi + Chi nhánh nhận                          │
│ - Loại hàng + Số lượng                                    │
│ - Trạng thái: pending (chờ), completed (xong)             │
│ Khi completed:                                            │
│   ├─ Trừ InventoryStock chi nhánh gửi                    │
│   ├─ Cộng InventoryStock chi nhánh nhận                  │
│   ├─ Ghi InventoryTransaction ×2                         │
│   └─ Cập nhật InventoryLot (FIFO)                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Bước 5: Tiêu Thụ Tự Động Từ Invoice                        │
│ (Chi tiết xem luồng Invoice, Bước 5)                       │
│ - consume_inventory_for_invoice()                          │
│ - Cập nhật InventoryStock, InventoryLot (FIFO)            │
│ - Ghi InventoryTransaction                                │
└─────────────────────────────────────────────────────────────┘
```

---

## VII. CẤU TRÚC DỮ LIỆU & CONSTRAINTS

### 7.1 Các Constraint Chính

```sql
/* Branch */
UNIQUE(name)
UNIQUE(phone)
UNIQUE(branch_code)
FK(manager_staff_id → Staff.id)

/* User */
UNIQUE(username)
FK(branch_id → Branch.id)
FK(staff_id → Staff.id)
CHECK(role IN ('super_admin', 'branch_manager', 'receptionist', 'inventory_controller', 'technician'))
CHECK(is_active IN (0, 1))

/* Staff */
UNIQUE(phone)
FK(branch_id → Branch.id)
UNIQUE(branch_id, phone)

/* StaffShift */
FK(branch_id → Branch.id)
FK(staff_id → Staff.id)
UNIQUE(staff_id, weekday)

/* Customer */
FK(branch_id → Branch.id)
UNIQUE(branch_id, phone)

/* Service */
FK(branch_id → Branch.id)

/* Service InventoryUsage */
FK(service_id → Service.id)
FK(item_id → InventoryItem.id)
UNIQUE(service_id, item_id)

/* Room */
FK(branch_id → Branch.id)
UNIQUE(branch_id, name)

/* Appointment */
FK(branch_id → Branch.id)
FK(customer_id → Customer.id) - NULLABLE
FK(room_id → Room.id) - NULLABLE
FK(service_id → Service.id) - REQUIRED
FK(technician_id → Staff.id)

/* AppointmentServiceItem */
FK(appointment_id → Appointment.id)
FK(service_id → Service.id)
UNIQUE(appointment_id, service_id)

/* InventoryStock */
FK(branch_id → Branch.id)
FK(item_id → InventoryItem.id)
UNIQUE(branch_id, item_id)

/* InventoryLot */
FK(branch_id → Branch.id)
FK(item_id → InventoryItem.id)
FK(supplier_id → Supplier.id) - NULLABLE
UNIQUE(branch_id, item_id, lot_code)

/* InvoicePayment */
FK(invoice_id → Invoice.id)
CHECK(payment_type IN ('payment', 'refund'))
CHECK(method IN ('cash', 'card', 'transfer'))

/* AppointmentServiceItem được xóa cascade */
Appointment → AppointmentServiceItem (ON DELETE CASCADE)
Invoice → InvoiceItem (ON DELETE CASCADE)
Invoice → InvoicePayment (ON DELETE CASCADE)
```

### 7.2 Indexes (Hiệu Suất)

```sql
/* Tìm kiếm nhanh */
Index(username) - User
Index(phone) - Staff, Branch, Customer
Index(branch_id) - Hầu hết bảng
Index(created_at) - ActivityLog
Index(status) - Invoice, Appointment

/* Constraint duy nhất */
Unique(name) - Branch, Service, InventoryItem, Supplier
Unique(code) - Invoice
```

---

## VIII. SECURITY & AUTHENTICATION

### 8.1 Authentication Mechanism

```python
# Session-based (không JWT)
session = {
    'user_id': int,
    'username': str,
    'role': str,
    'branch_id': int | None,
    'staff_id': int | None,
}

# Logout → Clear session
# Timeout → Flask default 30 min (đặt cấu hình)
```

### 8.2 Password Security

```python
# Hashing engines (Werkzeug)
scrypt (mặc định)  # Khuyến khích
pbkdf2            # Fallback
argon2            # Nếu cài thêm

# Min length
6 ký tự

# Check if needs rehash
old_hash = user.password_hash
if not is_password_hash(old_hash):
    # Hash plaintext lại
    user.set_password(plaintext)
```

### 8.3 Authorization Layer

```python
# 1. Decorator: @roles_required('super_admin', 'branch_manager')
# 2. Runtime: Kiểm tra scope branch_id
# 3. Entity-level: Kiểm tra entity.branch_id in user_scope

def check_access(user, entity):
    if user.is_super_admin:
        return True
    return entity.branch_id == user.branch_id
```

---

## IX. HẰNG SỐ & MAGIC NUMBERS

### 9.1 Thời Gian & Độ Lâu

| Tên | Giá Trị | Ý Nghĩa |
|-----|--------|--------|
| `Appointment.overdue_threshold` | 6 giờ | Lịch hẹn chưa xong sau 6 giờ → overdue |
| `MIN_PASSWORD_LENGTH` | 6 | Mật khẩu tối thiểu |
| Giờ làm việc mặc định | 08:00 - 21:00 | StaffShift |

### 9.2 Mã Vai Trò

```python
ROLES = {
    'super_admin',           # Quản trị
    'branch_manager',        # Quản lý chi nhánh
    'receptionist',          # Lễ tân
    'inventory_controller',  # Kiểm soát kho
    'technician',            # Kỹ thuật viên
}
```

### 9.3 Trạng Thái

```python
# Branch
status IN ('active', 'inactive')

# User
is_active: Boolean

# Appointment
status IN ('pending', 'completed', 'cancelled', 'overdue')

# Invoice
status IN ('paid', 'partial', 'unpaid', 'refunded', 'canceled')
payment_status IN ('paid', 'partial', 'unpaid')
payment_method IN ('cash', 'card', 'transfer')

# InventoryTransaction
type IN ('purchase', 'usage', 'transfer', 'adjustment')

# InventoryTransfer
status IN ('completed', 'pending')
```

---

## X. VALIDATION RULES

### 10.1 Số Điện Thoại

```python
# Pattern: 8-15 chữ số
PHONE_PATTERN = r"^\d{8,15}$"
is_valid_phone(value) → Bool
normalize_phone_digits(value) → str  # Loại bỏ non-digit
```

### 10.2 Ngày & Thời Gian

```python
# Lịch hẹn
appointment_date: DATE - không phép quá khứ
appointment_time: HH:MM - format "^\\d{2}:\\d{2}$"

# Staff shift
start_time, end_time: HH:MM

# Expiry date
Có thể null (không theo dõi)
```

### 10.3 Tiền Tệ

```python
# Decimal(12, 2) - 10 chữ số trước, 2 sau dấu chấm
Max: 9,999,999.99

# Không âm
discount_amount ≥ 0
tax_amount ≥ 0
quantity ≥ 0
```

---

## XI. EDGE CASES & BUSINESS RULES

### 11.1 Lịch Hẹn

```
1. Không được đặt lịch trong quá khứ
2. Nếu phòng chọn → Kiểm tra không xung đột
3. Kỹ thuật viên phải có shift vào ngày/giờ đó (optional kiểm tra)
4. Có thể đặt cho khách chưa có record (bypass khách hàng)
5. Auto-overdue sau 6 giờ từ appointment_time
```

### 11.2 Hóa Đơn

```
1. Mã hóa đơn auto-generate (INV-YYYYMMDD-005)
2. Không thể sửa hóa đơn đã canceled
3. Chỉ tiêu dùng hàng khi Paid = Total
4. Hoàn lại hàng nếu hóa đơn bị hủy
5. Thanh toán có thể dần (partial) hoặc 1 lần
6. Hoàn tiền → Tạo thêm InvoicePayment (refund type)
7. Customer stats cập nhật lúc hóa đơn paid full
```

### 11.3 Kho Hàng

```
1. Tồn kho của giá trị tiền hóa lệnh (không kiểm tra đủ hàng)
2. Lô hàng dùng FIFO (First-In-First-Out)
3. Cảnh báo: quantity ≤ min_stock
4. Chuyển hàng chỉ local (cùng DB, chỉ trừ/cộng tồn kho)
5. Điều chỉnh tồn kho (adjustment) cần ghi lý do
```

### 11.4 Tài Khoản & Phân Quyền

```
1. Nhân sự chỉ có 1 tài khoản (1:1)
2. Tài khoản phải gắn với nhân sự hoạt động
3. Chức vụ nhân sự phải phù hợp với vai trò tài khoản
4. Super Admin không thể xóa chính mình
5. Không thể tạo tài khoản super_admin qua giao diện
6. Mật khẩu ban đầu do admin set (không tự reset)
```

### 11.5 Chi Nhánh

```
1. Không thể xóa chi nhánh có dữ liệu (nhân sự, hóa đơn, lịch, etc.)
2. Mã chi nhánh format: CN + số (ví: CN001)
3. Mục quản lý (manager_staff_id) có thể đổi
4. Không thể đóng cửa chi nhánh còn dữ liệu chưa xử lý
```

---

## XII. DEPLOYMENT & CONFIGURATION

### 12.1 Environment Variables

```bash
# Bắt buộc
SECRET_KEY=your-secret-key-here

# Tùy chọn
DATABASE_URL=sqlite:///spa_mvp.db  (default)
FLASK_ENV=development|production
```

### 12.2 Database Initialization

```bash
# Tạo schema + migrations
python -m flask --app backend.app:create_app init-db

# Seed dữ liệu demo
python -m flask --app backend.app:create_app seed

# Reset (danger)
python -m flask --app backend.app:create_app reset-db --seed
```

### 12.3 Development Server

```bash
# Recommendation (Windows PowerShell)
powershell -ExecutionPolicy Bypass -File .\start_dev.ps1

# Manual
python -m flask --app backend.app:create_app --debug run --host 127.0.0.1 --port 5000
```

---

## XIII. METRICS & KPI

### 13.1 Dashboard Metrics

```
┌────────────────────────────────────────────────┐
│ Số Chi Nhánh (Branch Count)                    │
│  - Active branches / Total                     │
├────────────────────────────────────────────────┤
│ Số Nhân Sự (Staff Count)                       │
│  - Active staff / Total                        │
├────────────────────────────────────────────────┤
│ Số Dịch Vụ (Service Count)                     │
│  - Active services                             │
├────────────────────────────────────────────────┤
│ Tồn Kho Thấp (Low Stock)                       │
│  - Items quantity ≤ min_stock                  │
├────────────────────────────────────────────────┤
│ Hôm Nay (Today)                                │
│  - Số hóa đơn                                  │
│  - Doanh thu hôm nay                           │
├────────────────────────────────────────────────┤
│ Tháng Này (This Month)                         │
│  - Số hóa đơn                                  │
│  - Doanh thu tháng                             │
│  - Chi nhánh doanh thu cao nhất                │
│  - Chi nhánh doanh thu thấp nhất               │
└────────────────────────────────────────────────┘
```

---

## XIV. FUTURE ENHANCEMENTS (ROADMAP)

```
Phase 2:
  ✓ Multi-language support (EN, VI)
  ✓ Mobile app (React Native/Flutter)
  ✓ Real-time notifications (WebSocket)
  ✓ WhatsApp integration (appointment reminders)
  ✓ Payment gateway (Stripe, VNPay)
  ✓ SMS reminder

Phase 3:
  ✓ Advanced analytics (BI dashboard)
  ✓ Inventory forecasting (ML)
  ✓ Dynamic pricing
  ✓ Multi-currency support
  ✓ Audit trail exports
  ✓ Custom reports builder
```

---

## XV. SUMMARY TABLE

| Thành Phần | Mô Tả | Vai Trò |
|-----------|-------|--------|
| **Branch** | Chi nhánh spa | Dữ liệu cơ bản |
| **User** | Tài khoản đăng nhập | Authentication |
| **Staff** | Nhân viên | Tài nguyên |
| **Customer** | Khách hàng | Business entity |
| **Service** | Dịch vụ spa | Product |
| **Appointment** | Lịch hẹn | Core transaction |
| **Invoice** | Hóa đơn | Revenue tracking |
| **InventoryItem/Stock** | Hàng hóa & tồn kho | Expense tracking |
| **ActivityLog** | Nhật ký | Audit trail |

---

**Tài liệu này cập nhật lần cuối: April 20, 2026**  
**Dành cho nhóm phát triển & quản lý dự án**
