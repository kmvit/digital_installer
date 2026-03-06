# Digital Installer

Базовая инициализация проекта для этапа 1:
- Backend: Django + DRF + JWT
- База: PostgreSQL
- Frontend: React (Vite)
- Пользователи: кастомная модель `User` с ролевой моделью RBAC

## Структура
- `backend/` — API и бизнес-логика
- `frontend/` — клиентская часть
- `documentation/` — этапы и описание проекта

## Быстрый старт

1. Подготовка окружения:
   - Скопируйте `.env.example` в `.env`
   - Установите и запустите PostgreSQL (локально или в облаке)

2. Backend:
   - `python3 -m venv .venv`
   - `.venv/bin/pip install -r backend/requirements.txt`
   - `cd backend`
   - `../.venv/bin/python manage.py migrate`
   - `../.venv/bin/python manage.py seed_roles`
   - `../.venv/bin/python manage.py createsuperuser`
   - `../.venv/bin/python manage.py runserver`

3. Frontend:
   - `cd frontend`
   - `npm install`
   - `npm run dev`

## API (этап 1)
- `GET /api/health/` — healthcheck
- `POST /api/auth/token/` — получить JWT (`access`, `refresh`)
- `POST /api/auth/token/refresh/` — обновить `access`
- `GET /api/auth/me/` — профиль текущего пользователя

## RBAC (базовые роли)
Роли в `apps.users.models.RoleCode`:
- `administrator`
- `director`
- `project_manager`
- `foreman`
- `worker`
- `support_manager`
- `designer`
- `customer`
- `accountant`
