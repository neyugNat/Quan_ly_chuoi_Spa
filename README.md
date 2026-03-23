# QuanLySpa - He thong quan ly chuoi Spa (MVP)

Du an bai tap lon mon Lap trinh Python.

## Cau truc

- `backend/`: Flask API (Python)
- `frontend/`: ReactJS (Vite)
- `docs/`: diagram (use case, ERD, flow)

## Chay Backend (Flask)

Yeu cau: Python 3.11+

1) Tao venv va cai deps

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r backend/requirements.txt
```

2) Chay server

```bash
python -m flask --app backend.app run
```

Mac dinh: http://localhost:5000

## Chay Frontend (React)

Yeu cau: Node.js 20+

```bash
cd frontend
npm install
npm run dev
```

Mac dinh: http://localhost:5173