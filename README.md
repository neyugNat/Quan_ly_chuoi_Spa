# Quản Lý Chuỗi Spa (MVP)

Ứng dụng quản lý vận hành chuỗi spa theo mô hình server-rendered (Flask + Jinja), tập trung vào nghiệp vụ cốt lõi: chi nhánh, nhân sự, dịch vụ, kho, hóa đơn, báo cáo và phân quyền.

## 1. Mục tiêu MVP

- Quản lý theo phạm vi chi nhánh, không triển khai CRM phức tạp.
- Giao diện đơn giản, tối ưu thao tác nhập liệu hằng ngày.
- Dữ liệu mẫu đầy đủ để demo nhanh luồng vận hành.

## 2. Công nghệ

- Backend: Flask 3 + Flask-SQLAlchemy
- Frontend: Jinja2 + CSS thuần
- CSDL: SQLite

## 3. Cấu trúc chính

```text
backend/
	app.py                # app factory + lệnh CLI
	web.py                # blueprint + auth/session + helper dùng chung
	models.py             # schema + seed dữ liệu
	web_modules/          # module nghiệp vụ theo menu
	templates/web/        # giao diện Jinja
	static/style.css      # style toàn hệ thống
instance/
	spa_mvp.db            # database runtime mặc định
```

## 4. Cài đặt và chạy

### PowerShell (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python -m flask --app backend.app:create_app reset-db
python -m flask --app backend.app:create_app run --host 127.0.0.1 --port 5000
```

### Git Bash / môi trường có đường dẫn bin

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m flask --app backend.app:create_app reset-db
python -m flask --app backend.app:create_app run --host 127.0.0.1 --port 5000
```

Truy cập: http://127.0.0.1:5000/web/login

Tài khoản mẫu:

- admin / admin123
- manager / manager123

## 5. Quyền truy cập

- super_admin:
	- Xem toàn chuỗi
	- Lọc theo từng chi nhánh
	- Quản lý tài khoản branch_manager
- branch_manager:
	- Chỉ thao tác dữ liệu trong chi nhánh được gán
	- Thực hiện các thao tác vận hành hóa đơn và kho

## 6. Các lệnh hữu ích

```bash
python -m flask --app backend.app:create_app init-db
python -m flask --app backend.app:create_app seed
python -m flask --app backend.app:create_app reset-db --no-seed
```

## 7. Ghi chú cập nhật gần đây

- Dọn file thừa trong source (module/template khách hàng không còn dùng).
- Gom helper xử lý nhánh + trạng thái để giảm lặp code trong các module web.
- Chuẩn hóa nhãn trạng thái hóa đơn dùng chung cho UI và export CSV.
