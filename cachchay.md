# Cách Chạy Nhanh

## 1) Cài đặt môi trường

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

Git Bash:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## 2) Tạo lại dữ liệu demo

```bash
python -m flask --app backend.app:create_app reset-db
```

## 3) Chạy web

```bash
python -m flask --app backend.app:create_app run --host 127.0.0.1 --port 5000
```

Đăng nhập:

- http://127.0.0.1:5000/web/login
- admin: admin / admin123
- manager: manager / manager123

## 4) Danh sách màn hình

1. Tổng quan
2. Chi nhánh
3. Nhân sự
4. Dịch vụ
5. Kho
6. Hóa đơn
7. Báo cáo
8. Tài khoản

## 5) Lệnh hỗ trợ

```bash
python -m flask --app backend.app:create_app init-db
python -m flask --app backend.app:create_app seed
python -m flask --app backend.app:create_app reset-db --no-seed
```
