# Cach chay Docker Compose cho QuanLySpa

Tai lieu nay huong dan cach chay project tren server bang Docker Compose.
Tat ca lenh ben duoi duoc chay trong thu muc `docker/`.

## 1) Setup lan dau tren server

### 1.1 Cai Docker + Compose plugin (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Dang xuat/dang nhap lai sau khi add user vao group `docker`.

### 1.2 Clone code va chay compose

```bash
git clone <repo-url> QuanLySpa
cd QuanLySpa/docker
cp .env.example .env
docker compose up -d --build
```

Mac dinh se mo:
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:5000`

## 2) Cac file Docker da co

- `docker-compose.yml`: 2 service `backend` + `frontend`
- `backend/Dockerfile`: Python 3.11
- `frontend/Dockerfile`: build bang Node 20, serve bang nginx
- DB SQLite duoc luu bind mount tai `docker/data/instance/spa.db`

## 3) Chay nhung lan sau

```bash
cd QuanLySpa/docker
docker compose up -d
```

Dung he thong:

```bash
docker compose down
```

Build lai image khi co thay doi code:

```bash
docker compose up -d --build
```

## 4) Reset du lieu demo

Backend startup se auto chay migration + seed (idempotent).
Neu can reset sach DB demo:

```bash
cd QuanLySpa/docker
docker compose down
rm -rf data
docker compose up -d --build
```

Sau khi reset, file DB moi duoc tao lai o `docker/data/instance/spa.db`.

## 5) Xem logs

Tat ca service:

```bash
docker compose logs -f
```

Rieng backend:

```bash
docker compose logs -f backend
```

Rieng frontend:

```bash
docker compose logs -f frontend
```

## 6) Tai khoan demo

- Super admin: `admin` / `admin123`
- Branch manager (Chi nhanh 1): `manager_b1` / `manager123`
- Reception (Chi nhanh 1): `reception_b1` / `reception123`
- Cashier (Chi nhanh 1): `cashier_b1` / `cashier123`
- Technician (Chi nhanh 2): `technician_b2` / `technician123`
- Warehouse (Chi nhanh 2): `warehouse_b2` / `warehouse123`

## 7) Role -> pages tom tat

- `super_admin`: full, landing `/dashboard`
- `branch_manager`: full theo chi nhanh, landing `/dashboard`
- `reception`: `/pos`, `/customers`, `/appointments`, landing `/pos`
- `cashier`: `/pos`, `/customers`, landing `/pos`
- `warehouse`: `/inventory`, landing `/inventory`
- `technician`: `/technician`, landing `/technician`

## 8) Doi API URL frontend

Frontend doc `VITE_API_URL` tai build time.
Mac dinh trong compose: `http://localhost:5000`.

Neu can doi domain/public IP backend:

1. Sua file `docker/.env`
2. Dat lai bien, vi du:

```env
VITE_API_URL=http://your-server-ip:5000
```

3. Build lai frontend:

```bash
docker compose up -d --build frontend
```

## 9) Troubleshooting nhanh

1. Trung port 5000 hoac 5173
   - Doi mapping port trong `docker-compose.yml` hoac tat process dang chiem port.

2. Login fail sau khi da doi password demo truoc do
   - Seed se reset password demo ve mac dinh.
   - Chay lai `docker compose restart backend` de backend startup seed lai.

3. Khong thay du lieu demo
   - Kiem tra log backend co chay `db upgrade` va `seed` hay khong.
   - Kiem tra file `docker/data/instance/spa.db` co ton tai.

4. Loi CORS khi goi API tu frontend
   - Backend dang set `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`.
   - Neu truy cap frontend bang domain/IP khac, can cap nhat `CORS_ORIGINS` trong `docker-compose.yml` roi `docker compose up -d --build backend`.
