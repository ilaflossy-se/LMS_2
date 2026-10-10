# LMS — прототип (React + Flask + PostgreSQL)

## Деплой на Render (бесплатно, без Docker)
1. Загрузите папку проекта в GitHub-репозиторий.
2. Render → New → Blueprint → выберите репозиторий. Render создаст БД `lms-db`, API `lms-api` и сайт `lms-web` по `render.yaml`.
3. Когда спросит `VITE_API`, вставьте URL API (https://lms-api-XXXX.onrender.com). Если URL ещё неизвестен: оставьте пустым,
   дождитесь деплоя `lms-api`, затем в `lms-web` → Environment задайте `VITE_API` и нажмите Manual Deploy → Clear build cache & deploy.
4. Откройте URL сайта `lms-web`.

Таблицы и демо-данные создаются автоматически при первом запуске API.
Бесплатный API «засыпает» после простоя, первый запрос может идти ~30–60 с.

## Локально
    # PostgreSQL: пользователь lms / пароль lms / база lms (или задайте DATABASE_URL)
    cd backend && pip install -r requirements.txt && python app.py
    cd frontend && npm install && npm run dev

Вход: «Connect with OpenID Connect» (имитация) или «Demo: sign in as teacher».
