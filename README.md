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
   - `../.venv/bin/python manage.py createsuperuser`
   - `../.venv/bin/python manage.py runserver`

3. Frontend:
   - `cd frontend`
   - `npm install`
   - `npm run dev`

## API (этап 1-2)
- `GET /api/health/` — healthcheck
- `POST /api/auth/token/` — получить JWT (`access`, `refresh`)
- `POST /api/auth/token/refresh/` — обновить `access`
- `GET /api/auth/me/` — профиль текущего пользователя
- `GET/POST /api/admin/users/` — список/создание пользователей
- `GET/PATCH/DELETE /api/admin/users/{id}/` — управление пользователем
- `GET/POST /api/admin/brigades/` — список/создание бригад
- `GET/PATCH/DELETE /api/admin/brigades/{id}/` — управление бригадой
- `GET/POST /api/admin/settings/` — базовые настройки (ключ-значение)
- `GET/POST /api/admin/pricelists/` — CRUD баз расценок
- `GET/PATCH/DELETE /api/admin/pricelists/{id}/` — управление базой расценок
- `GET/POST /api/admin/pricelist-items/` — CRUD позиций расценок
- `GET/PATCH/DELETE /api/admin/pricelist-items/{id}/` — управление позицией расценки
- `GET/POST /api/admin/objects/` — простой CRUD объектов (название + база расценок)
- `GET/PATCH/DELETE /api/admin/objects/{id}/` — управление объектом
- `POST /api/admin/pricelists/import/` — заглушка импорта (501)
- `GET /api/admin/pricelists/export/` — заглушка экспорта (501)

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
