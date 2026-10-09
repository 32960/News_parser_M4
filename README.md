# AINEWS — AI-генератор постов для Telegram

Учебный сервис: собирает новости с сайта и из Telegram-каналов, генерирует короткий пост через OpenAI и публикует его в целевой Telegram-канал по расписанию. Управление — через REST API и Swagger UI.

ТЗ проекта: [Project M4-1.md](Project%20M4-1.md)

---

## Что умеет сервис

Цепочка работы:

1. Редактор добавляет источники (сайт и/или Telegram) через API.
2. Сервис по расписанию (или вручную) собирает новости из включённых источников.
3. Для новых новостей ИИ готовит короткий пост в стиле Telegram-канала.
4. Готовые посты встают в очередь и уходят в целевой канал (по расписанию UTC или вручную).
5. Через API можно смотреть новости и посты, включать/выключать источники, перезапускать шаги.

Кратко по возможностям:

- сбор новостей с поддерживаемого сайта и из публичных Telegram-каналов;
- защита от дублей (по URL статьи или паре ID канала + сообщения);
- генерация текста через OpenAI (автоматически и вручную);
- публикация в Telegram через Telethon;
- фоновые задачи на Celery + расписание Celery Beat;
- управление и мониторинг через REST API и Swagger UI (`/docs`);
- просмотр задач Celery в Flower (`/`, порт 5555) — для отладки.

---

## Стек

- Python 3.14+, FastAPI, SQLModel, PostgreSQL
- Celery, Redis, Celery Beat
- Telethon, OpenAI API
- Docker Compose
- Зависимости: `pyproject.toml` + `uv.lock` (пакетный менеджер [uv](https://github.com/astral-sh/uv))

---

## Поддерживаемые источники

### Сайты (`type=site`)

Сейчас один парсер. API принимает **только** этот адрес:

```text
https://habr.com/ru/rss/articles/
```

Любой другой site-URL вернёт **HTTP 422**.

### Telegram (`type=telegram`)

Общий парсер. В `url` можно передать:

- `@username`
- `https://t.me/username`
- `username`

При сохранении адрес нормализуется к виду `https://t.me/username`.

---

## Быстрый старт (Docker)

### 1. Клонировать и настроить окружение

```bash
cp .env.example .env
```

Заполните в `.env` секреты (см. раздел «Переменные окружения»).  
Для Docker удобно оставить:

```env
TELEGRAM_SESSION_PATH=telegram_sessions/session
```

`DATABASE_URL` / Redis URL внутри Compose переопределяются на сервисы `postgres` и `redis`.

### 2. Авторизация Telegram (один раз)

Нужны `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` с https://my.telegram.org  
Аккаунт должен читать каналы-источники и иметь право писать в целевой канал (`TELEGRAM_TARGET_CHANNEL`).

Локально (из корня проекта, с установленными зависимостями):

```bash
uv sync
uv run python -m app.telegram.authorize
```

Введите телефон, код из Telegram и пароль 2FA при необходимости.  
Файл сессии появится в `telegram_sessions/` (в Git не попадает).

> В Celery-воркере интерактивный логин **не** запускается: при битой сессии задача завершится с ошибкой в логе.

### 3. Поднять сервисы

```bash
docker compose up --build
```

Сервисы:

| Сервис | Роль |
|---|---|
| `backend` | FastAPI на http://localhost:8000 |
| `celery-worker` | Очередь `celery` (генерация ИИ) |
| `celery-telegram-worker` | Очередь `telegram` (сбор + публикация), concurrency=1 |
| `celery-beat` | Расписание: сбор каждые 30 мин, публикация в `:00` и `:30` UTC |
| `flower` | Веб-мониторинг Celery на http://localhost:5555 (для отладки, в ТЗ не обязателен) |
| `postgres` | БД |
| `redis` | Брокер Celery |

Swagger: http://localhost:8000/docs  
Flower: http://localhost:5555

---

## Локальный запуск без Docker (кратко)

Нужны запущенные PostgreSQL и Redis, заполненный `.env`.

```bash
uv sync
uv run python -m app.telegram.authorize
uv run uvicorn app.main:app --reload --port 8000
uv run celery -A celery_app worker -l info -Q celery -c 2
uv run celery -A celery_app worker -l info -Q telegram -c 1
uv run celery -A celery_app beat -l info
uv run celery -A celery_app flower --port=5555
```

---

## Переменные окружения

Шаблон: [`.env.example`](.env.example). Локальный `.env` в репозиторий не коммитится.

| Переменная | Назначение |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Для контейнера Postgres |
| `DATABASE_URL` | Подключение SQLAlchemy (`postgresql+psycopg://...`) |
| `CELERY_BROKER_URL` | Redis-брокер |
| `CELERY_RESULT_BACKEND` | Backend результатов Celery |
| `TELEGRAM_SESSION_PATH` | Путь/имя файла сессии Telethon |
| `TELEGRAM_API_ID` | API ID приложения Telegram |
| `TELEGRAM_API_HASH` | API hash |
| `TELEGRAM_TARGET_CHANNEL` | Канал для публикации (`@name` или id) |
| `OPENAI_API_KEY` | Ключ OpenAI |
| `OPENAI_MODEL` | Модель (например `gpt-4o-mini`) |


---

## Пример работы через API

Ниже — типичный сценарий. Удобнее повторить в Swagger `/docs`.

### 1. Добавить источники

```bash
curl -X POST http://localhost:8000/api/sources/ \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"site\",\"name\":\"Habr\",\"url\":\"https://habr.com/ru/rss/articles/\",\"enabled\":true}"

curl -X POST http://localhost:8000/api/sources/ \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"telegram\",\"name\":\"Demo\",\"url\":\"https://t.me/durov\",\"enabled\":true}"
```

### 2. Запустить сбор

```bash
curl -X POST http://localhost:8000/api/parse/
# → 202 {"task_id":"..."}
```

Через некоторое время:

```bash
curl http://localhost:8000/api/news/
```

### 3. Генерация (если нужна вручную)

После сбора новые новости обычно уже ставят задачу генерации сами. Вручную:

```bash
curl -X POST http://localhost:8000/api/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"news_id\":\"<uuid из /api/news/>\"}"
# → 202 {"post_id":"..."}
```

Статус поста:

```bash
curl http://localhost:8000/api/posts/<post_id>/
```

### 4. Публикация вручную

Когда `status=generated`:

```bash
curl -X POST http://localhost:8000/api/posts/<post_id>/publish/
# → 202 {"post_id":"..."}
```

Повтор для уже `published` → **200** и сохранённый пост (без повторной отправки).

Автоматически Beat отправляет **один** готовый пост в `HH:00` и `HH:30` UTC.

---

## Расписание

| Задача | Когда |
|---|---|
| Сбор новостей из `enabled=true` | каждые 30 минут |
| Публикация одного поста со статусом `generated` | каждую минуту `0` и `30`, часовой пояс **UTC** |

Порядок очереди публикации: сначала меньший `generated_at`, при равенстве — меньший `id`.

---

## Структура проекта (кратко)

```text
app/
  api/          # роутеры и Pydantic-схемы
  services/     # бизнес-логика
  parsers/      # Habr + Telegram
  ai/           # OpenAI
  telegram/     # Telethon client + authorize
  models.py     # таблицы БД
  tasks.py      # Celery-задачи
celery_app.py
docker-compose.yaml
```

---

## Известные ограничения

1. После смены схемы БД при отсутствии Alembic может понадобиться пересоздать volume Postgres (`docker compose down -v`) - учебные данные пропадут.
2. Один файл сессии Telethon: задачи сбора и публикации идут в очередь `telegram` с concurrency=1.
3. Если процесс упадёт **после** успешной отправки в Telegram, но **до** записи `published` в БД, при повторе возможен дубль в канале (для учебной версии по ТЗ допустимо).
4. Поддерживается один сайт (Habr RSS); новый сайт = новый парсер в коде.
5. Авторизации в API нет - по ТЗ для локального запуска не обязательна.

---

## Чеклист по требованиям

Обязательный минимум из ТЗ (для проверяющего).

| Пункт | Статус |
|---|---|
| Сбор с поддерживаемого сайта (Habr RSS) | Сделано |
| Сбор из публичных Telegram-каналов | Сделано |
| Управление источниками (CRUD, `enabled`) | Сделано |
| Дедупликация новостей в БД | Сделано |
| AI-генерация (авто + ручная), `summary` / `raw_text` | Сделано |
| Публикация по расписанию UTC `:00` / `:30` и вручную | Сделано |
| Celery + Redis + Celery Beat | Сделано |
| API + Swagger `/docs` | Сделано |
| Логирование ошибок сбора / ИИ / публикации | Сделано |
| README, `.env.example`, секреты не в Git | Сделано |

---

## Напоминания и идеи на потом

Не входит в обязательный чеклист. Можно вернуться позже (часть — бонусы из ТЗ).

| Тема | Сейчас | Заметка |
|---|---|---|
| Авторизация API + роли | Не сделано | В ТЗ — бонус; для локального запуска не требуется |
| Alembic-миграции | Не сделано | Сейчас схема создаётся через `create_all` при старте |
| Автоматические retry OpenAI / Telegram | Не сделано | Повтор уже можно сделать вручную через API |
| Защита от дубля в канале при крэше после send | Не сделано | В ТЗ — дополнительная задача; учебный минимум допускает проверку только статуса в БД |
| Flower | Сделано | Удобно для отладки Celery; в обязательную часть ТЗ не входит |
| Больше сайт-парсеров / RSS через API | Не сделано | Бонус «новые источники» |
| Тесты основных сценариев | Не сделано | Бонус из ТЗ |
