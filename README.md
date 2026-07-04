Слои:

- app/main.py — точка входа FastAPI. На старте поднимает схему Neo4j, дальше раздаёт API на /api/v1.

- app/api/v1/endpoints/ — ручки: auth (логин), users (создание/профиль), graph (запись сущностей/связей + окрестность), query (поиск), review (автообзор), analytics (пробелы, сравнение, рекомендации), audit (журнал действий).

- app/services/ — бизнес-логика:
  - ingestion — читает файл, определяет язык.
  - nlp — тянет из текста сущности, синонимы, числовые ограничения (пока заглушка с готовым интерфейсом).
  - graph — пишет/читает Neo4j через Cypher.
  - search — фильтры (география, годы, confidence, глубина обхода графа).
  - analytics — обзоры, пробелы «материал × процесс × условие», сравнения.
  - security — bcrypt + JWT, лог аудита.

- app/db/ — подключения: sql/session.py (PostgreSQL), neo4j/driver.py (Neo4j). __init__ сделан ленивым, чтобы тесты не падали без БД.

- app/models/sql/ — таблицы: User (с Role из ТЗ), AuditLog, FactVersion (версионирование выводов).

- app/schemas/ — Pydantic-модели запросов/ответов.

- ui/streamlit_app.py — лёгкий веб-интерфейс на 4 вкладки, дёргает API.

- scripts/ingest.py — CLI: файл → NLP → граф.

- scripts/create_user.py — CLI: создать пользователя/админа.

- alembic/versions/0001_initial.py — миграция SQL (создаёт 3 таблицы).

- docker-compose.yml — поднимает postgres + neo4j + api + ui одной командой.

Запуск:
Создайте файл `.env` со своими секретами (можно взять за основу `.env.example`).
docker compose up --build

API: http://localhost:8000, UI: http://localhost:8501
