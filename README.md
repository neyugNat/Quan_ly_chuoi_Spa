# Quản Lý Chuỗi Spa

Ứng dụng quản lý vận hành chuỗi spa theo mô hình server-rendered (Flask + Jinja), tập trung vào nghiệp vụ cốt lõi:

- Chi nhánh
- Nhân sự
- Dịch vụ
- Kho
- Hóa đơn
- Báo cáo
- Tài khoản và phân quyền theo vai trò

## 1. Công nghệ

- Python + Flask 3
- Flask-SQLAlchemy
- Jinja2 + CSS thuần
- SQLite

## 2. Yêu cầu môi trường

- Python 3.10+ (khuyến nghị 3.11+)
- Windows PowerShell hoặc Git Bash

## 3. Cấu trúc chính

```text
backend/
	app.py                # App factory + CLI command
	web.py                # Blueprint web + auth/session + helper dùng chung
	models.py             # Schema, migration helper, seed data
	web_modules/          # Module nghiệp vụ theo từng màn hình
	templates/web/        # Giao diện Jinja
	static/style.css      # CSS toàn hệ thống
instance/
	spa_mvp.db            # SQLite runtime mặc định
start_dev.ps1           # Script chạy dev server cho Windows
```

## 4. Cài đặt

### 4.1 PowerShell (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

### 4.2 Git Bash

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## 5. Cách chạy ứng dụng

### Cách 1: Chạy nhanh bằng script (khuyến nghị cho Windows)

```powershell
powershell -ExecutionPolicy Bypass -File .\start_dev.ps1
```

Script sẽ:

- Dùng đúng Python trong `.venv`
- Xóa biến `DATABASE_URL` để tránh trỏ nhầm DB ngoài dự án
- Dọn process đang chiếm cổng trước khi chạy lại
- Chạy Flask ở chế độ `--debug`

Bạn có thể đổi cổng:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_dev.ps1 -Port 5001
```

### Cách 2: Chạy thủ công

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app run --host 127.0.0.1 --port 5000
```

Nếu muốn auto-reload khi sửa code:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app --debug run --host 127.0.0.1 --port 5000
```

## 6. Khởi tạo dữ liệu

```powershell
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app init-db
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app seed
```

Reset lại database demo:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app reset-db
```

Reset nhưng không seed:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app reset-db --no-seed
```

## 7. Đăng nhập

- URL: http://127.0.0.1:5000/web/login
- Tài khoản mẫu:
	- `admin / admin123`
	- `manager / manager123`

## 8. Vai trò chính

- `super_admin`: quản lý toàn chuỗi, xem/lọc theo chi nhánh, quản lý tài khoản vận hành.
- `branch_manager`: thao tác trong phạm vi chi nhánh được gán.
- `receptionist`, `inventory_controller`, `technician`: thao tác theo quyền đã phân.

## 9. Lỗi thường gặp

- Không chạy được bằng `python -m flask ...`
	- Dùng trực tiếp Python trong `.venv`:
		- `.\.venv\Scripts\python.exe -m flask --app backend.app:create_app run ...`
- Bị trỏ nhầm database
	- Chạy trước lệnh:
		- `Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue`
- Cổng đã bị chiếm
	- Đổi cổng hoặc dùng `start_dev.ps1` để script tự dọn cổng.
