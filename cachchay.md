# Cach chay va demo QuanLySpa (MVP)

Tai lieu nay huong dan:
- Setup lan dau va cach chay lai cho nhung lan sau
- Seed du lieu demo va hanh vi reset password demo
- Cach check day du feature theo role va theo luong end-to-end
- Lam ro nghiep vu void invoice

Pham vi: MVP Release 1.

---

## 1) Yeu cau moi truong

1) Python 3.11+
2) Node.js 20+
3) Chay lenh tai thu muc goc project (noi co `backend/`, `frontend/`)

Ports mac dinh:
- Backend: http://localhost:5000
- Frontend: http://localhost:5173

Duong dan DB SQLite:
- `instance/spa.db`

---

## 2) Chay lan dau tien

### 2.1) Backend (Flask)

WSL/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m flask --app backend.app db upgrade
python -m flask --app backend.app seed
python -m flask --app backend.app run --host 0.0.0.0 --port 5000
```

Windows (PowerShell):

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python -m flask --app backend.app db upgrade
python -m flask --app backend.app seed
python -m flask --app backend.app run --host 0.0.0.0 --port 5000
```

Windows (cmd):

```bash
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r backend/requirements.txt
python -m flask --app backend.app db upgrade
python -m flask --app backend.app seed
python -m flask --app backend.app run --host 0.0.0.0 --port 5000
```

### 2.2) Frontend (React/Vite)

WSL/Linux:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Windows (PowerShell/cmd):

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

---

## 3) Chay nhung lan tiep theo

Thong thuong khong can cai lai package.

WSL/Linux:

```bash
source .venv/bin/activate
python -m flask --app backend.app run --host 0.0.0.0 --port 5000
```

Windows (PowerShell):

```bash
.\.venv\Scripts\Activate.ps1
python -m flask --app backend.app run --host 0.0.0.0 --port 5000
```

Windows (cmd):

```bash
.venv\Scripts\activate.bat
python -m flask --app backend.app run --host 0.0.0.0 --port 5000
```

Frontend (ca WSL/Linux va Windows):

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Neu can reset du lieu demo va password demo, chay lai:

```bash
python -m flask --app backend.app seed
```

Tuy chon: auto seed khi backend startup (`AUTO_SEED_DEMO=1`).

WSL/Linux:

```bash
AUTO_SEED_DEMO=1 python -m flask --app backend.app run --host 0.0.0.0 --port 5000
```

Windows (PowerShell):

```bash
$env:AUTO_SEED_DEMO="1"
python -m flask --app backend.app run --host 0.0.0.0 --port 5000
```

Windows (cmd):

```bash
set AUTO_SEED_DEMO=1
python -m flask --app backend.app run --host 0.0.0.0 --port 5000
```

---

## 4) Seed demo va tai khoan demo

Lenh seed chuan:

```bash
python -m flask --app backend.app seed
```

Tai khoan demo:
- Super admin: `admin` / `admin123`
- Branch manager (Chi nhanh 1): `manager_b1` / `manager123`
- Reception (Chi nhanh 1): `reception_b1` / `reception123`
- Cashier (Chi nhanh 1): `cashier_b1` / `cashier123`
- Technician (Chi nhanh 2): `technician_b2` / `technician123`
- Warehouse (Chi nhanh 2): `warehouse_b2` / `warehouse123`

Luu y quan trong ve seed:
- Seed co tinh chat idempotent cho du lieu mau.
- Seed se dat lai password cua tai khoan demo ve gia tri mac dinh ben tren.
- Neu da doi password demo truoc do, sau khi seed can dang nhap lai bang password mac dinh.

---

## 5) Routes, quyen role va landing sau login

Nguyen tac landing hien tai:
- Sau login, he thong di den route dau tien ma role do duoc phep theo thu tu NAV sidebar (first allowed sidebar item order).

Route theo role (tom tat de demo):
- `super_admin`: full, landing `/dashboard`
- `branch_manager`: full theo chi nhanh, landing `/dashboard`
- `reception`: `/pos`, `/customers`, `/appointments`, landing `/pos`
- `cashier`: chi `/pos` va `/customers`, khong vao `/appointments`, landing `/pos`
- `warehouse`: chi `/inventory`, landing `/inventory`
- `technician`: chi `/technician`, landing `/technician`

---

## 6) Invoice void: y nghia, rang buoc, ai duoc dung

Y nghia:
- Void invoice = huy hoa don nghiep vu (status `voided`), khong phai xoa record khoi DB.

Rang buoc:
- Chi void duoc invoice trong cung branch dang scope.
- Khong void lai invoice da `voided`.
- Khong void duoc invoice da co payment (`paid_amount > 0`).
- Invoice da `voided` se khong cho them payment.

Role duoc void:
- `super_admin`, `branch_manager`

Role khong duoc void:
- `reception`, `cashier`, `technician`, `warehouse`

---

## 7) Checklist demo day du theo role

### 7.1) Super admin (`admin/admin123`)

1) Login, vao `/dashboard`
2) Switch branch va xac nhan data doi theo branch
3) `/branches`: tao/sua branch
4) `/audit-logs`: thuc hien thao tac nghiep vu roi reload de thay log moi
5) `/users` (neu co): kiem tra danh sach tai khoan

### 7.2) Branch manager (`manager_b1/manager123`)

1) Login, landing `/dashboard`
2) `/services`: tao/sua dich vu
3) `/packages`: tao/sua goi lieu trinh
4) `/resources`: tao/sua tai nguyen
5) `/inventory`: kiem tra ton kho branch
6) `/reports`: kiem tra revenue/inventory report theo branch
7) Test void invoice (chi manager/admin): tao invoice chua thanh toan roi void

### 7.3) Reception (`reception_b1/reception123`)

1) Login, landing `/pos`
2) `/customers`: tao customer, tim/loc
3) `/appointments`: tao lich hen, test conflict
4) Tu `/pos`: tao invoice va payment
5) Xac nhan reception khong co quyen void invoice

### 7.4) Cashier (`cashier_b1/cashier123`)

1) Login, landing `/pos`
2) Xac nhan truy cap duoc `/customers`
3) Tao invoice/payment tren POS (khong con ghi chu 403 cu)
4) Thu vao `/appointments` de xac nhan bi chan quyen

### 7.5) Technician (`technician_b2/technician123`)

1) Login, landing `/technician`
2) Mo 1 appointment cua minh: check-in -> ghi note SOAP -> check-out
3) Xac nhan khong vao duoc cac page quan tri

### 7.6) Warehouse (`warehouse_b2/warehouse123`)

1) Login, landing `/inventory`
2) Xac nhan chi vao duoc `/inventory`
3) Tao/ghi nhan giao dich kho (neu UI co) va doi chieu ton kho

---

## 8) Checklist end-to-end (luong nghiep vu)

### Flow A: Customer + appointment + technician hoan tat

1) (Reception) Tao customer
2) (Reception) Tao appointment
3) (Technician) Vao `/technician`, check-in, ghi note, check-out
4) (Reception/Manager) Kiem tra status appointment da completed

### Flow B: POS billing + payment + report

1) (Reception hoac Cashier) Tao invoice tu POS
2) Tao payment (`cash` hoac `transfer`)
3) (Manager/Admin) Mo `/reports` va xac nhan doanh thu tang dung branch

### Flow C: Invoice void rule

1) (Manager/Admin) Tao invoice chua co payment
2) Void invoice thanh cong
3) Thu tao payment cho invoice da void -> phai bi chan
4) Thu void lai invoice da void -> phai bi chan

---

## 9) Test tu dong nhanh

Backend tests:

WSL/Linux:

```bash
source .venv/bin/activate
python -m pytest -q
```

Windows (PowerShell):

```bash
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Windows (cmd):

```bash
.venv\Scripts\activate.bat
python -m pytest -q
```

Frontend build check:

```bash
cd frontend
npm run build
```

---

## 10) Troubleshoot nhanh (ban moi)

1) Login duoc nhung API bao `branch_required`
   - Kiem tra da chon branch tren sidebar (neu user co nhieu branch)
   - Kiem tra LocalStorage co `branch_id` hop le

2) API 401
   - Logout/login lai
   - Kiem tra backend dang chay tai `http://localhost:5000`

3) Khong thay du lieu demo hoac du lieu cu bi lech
   - Chay lai `python -m flask --app backend.app seed`
   - Kiem tra file DB tai `instance/spa.db`

4) Da doi password demo truoc do nhung login that bai
   - Seed se reset password demo ve mac dinh, dung lai password trong muc tai khoan demo

5) Khong start duoc do trung port
   - Dam bao backend dung port `5000`, frontend dung port `5173`

6) Void invoice that bai
   - Kiem tra role co phai `super_admin` hoac `branch_manager`
   - Kiem tra invoice chua co payment va chua bi void truoc do
