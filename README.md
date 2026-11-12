# Projeto Final MWD

Monorepo com o frontend e o backend do projeto.

## Estrutura

- `frontend/` — aplicação React + Vite
- `backend/` — API REST com Django + Django REST Framework

## Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate          
pip install -r requirements.txt
python manage.py migrate
python manage.py importar_membros   # carga inicial dos membros atuais a partir da API do NEO
python manage.py criar_projetos_exemplo   # (opcional) projetos FICTÍCIOS para desenvolvimento
python manage.py runserver       # http://127.0.0.1:8000/api/
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```
