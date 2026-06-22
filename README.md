# Linux.do Relay and Public API Monitoring System

[![English](https://img.shields.io/badge/Language-English-blue)](#)
[![简体中文](https://img.shields.io/badge/Language-简体中文-green)](README_zh.md)

A post monitoring and AI filtering dashboard for the [linux.do](https://linux.do/) forum. The system fetches the latest topics, performs a rough initial filter using local keywords, and then calls a Large Language Model (LLM) for semantic classification, summarization, and value scoring. It is ideal for tracking relay stations, public APIs, welfare benefits, and service anomalies.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-42B883?logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

## Preview

![Dashboard preview](./粘贴的图像.png)

## Features

- **Incremental Crawling**: Crawls `linux.do/latest.json` and supports collecting posts from the last N hours.
- **Deduplication**: Automatically skips posts already in the database to reduce redundant processing and LLM API costs.
- **AI Filtering**: Local keyword rough filtering combined with LLM semantic fine-filtering to output category, summary, relevance, and a value score from 1-5.
- **Multi-Protocol Support**: Supports OpenAI-compatible and Anthropic protocols, configurable dynamically via the admin dashboard.
- **FastAPI Backend**: Exposes endpoints for post list, dashboard statistics, background synchronization, sync progress, and admin configuration.
- **Vue 3 Frontend**: Provides a monitoring dashboard, system settings, manual synchronization, and data overview.
- **Automated Scheduler**: Uses APScheduler to automatically crawl incremental posts from the past 24 hours daily at 08:00.
- **Flexible Database**: SQLite by default, with support for switching to MySQL or TiDB Serverless via the `DATABASE_URL` environment variable.
- **Docker Ready**: Supports multi-stage builds. The backend can directly host the built frontend static assets.

## Tech Stack

| Layer | Stack |
| --- | --- |
| Frontend | Vue 3, Vite, Axios |
| Backend | FastAPI, Uvicorn, Pydantic |
| Data Storage | SQLAlchemy, SQLite, MySQL / TiDB |
| Jobs / Scheduler | APScheduler |
| Crawler | `curl_cffi` / `requests` |
| LLM | OpenAI-compatible API, Anthropic API |
| Deployment | Docker, Render-compatible |

## Quick Start

### 1. Backend

```bash
pip install -r requirements.txt
uvicorn server:app --reload --port 8501
```

The backend runs at `http://localhost:8501`. On first start, it automatically creates the database tables.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`. Vite proxies `/api` requests to `http://localhost:8501`.

### 3. First Login

Open the frontend and sign in with the default password:

```text
admin123
```

On first use, the application requires you to:
- Change the admin password to a stronger one.
- Configure the LLM provider, API key, base URL, and model name.

## Configuration

Runtime configuration is stored in the database and can be updated from the admin panel.

| Config | Description |
| --- | --- |
| `ADMIN_PASSWORD` | Optional initial admin password or cloud password reset value |
| `DATABASE_URL` | Optional database URL; defaults to local SQLite `data.db` |
| LLM Provider | `openai` or `anthropic` |
| LLM API Key | Stored in database after setup |
| LLM Base URL | Supports official endpoints or compatible gateways |
| LLM Model | Model used for semantic filtering |

For public repositories, do not commit real API keys, database URLs, cookies, or proxy credentials.

## Docker

Build the image:

```bash
docker build -t linuxdo-monitor .
```

Run with a persisted SQLite database:

```bash
touch data.db
docker run -d \
  -p 8501:8501 \
  --name linuxdo-monitor \
  -v "$PWD/data.db":/app/data.db \
  linuxdo-monitor
```

Open `http://localhost:8501` after the container starts.

Useful commands:

```bash
docker logs -f linuxdo-monitor
docker stop linuxdo-monitor
docker start linuxdo-monitor
docker rm -f linuxdo-monitor
```

## Cloud Deployment

The project can be deployed as a Docker web service on platforms such as Render.

Recommended environment variables:

```text
DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:<port>/<database>?ssl_ca=/etc/ssl/certs/ca-certificates.crt
ADMIN_PASSWORD=<your-initial-admin-password>
```

Notes:
- If `DATABASE_URL` starts with `mysql://`, the application automatically rewrites it to `mysql+pymysql://`.
- If the platform sleeps idle containers, use an external uptime monitor to request `/api/stats` periodically to keep the scheduler running.
- The daily scheduled job runs at 08:00 in the `Asia/Shanghai` timezone.

## CLI Usage

You can run the collection pipeline without starting the web server:

```bash
python main.py --hours 24
```

This fetches topics active in the last 24 hours, filters them, and writes results to the configured database.

## Project Structure

```text
.
├── config.py              # Database URL, crawler limits and keyword configuration
├── crawler.py             # linux.do latest topics crawler
├── database.py            # SQLAlchemy engine, sessions and data access helpers
├── filter.py              # Keyword filter and LLM semantic filter
├── main.py                # Collection pipeline and CLI entry point
├── models.py              # ORM models
├── scheduler.py           # Daily background job
├── server.py              # FastAPI app and REST API
├── Dockerfile             # Multi-stage frontend/backend image
├── requirements.txt       # Python dependencies
├── 粘贴的图像.png          # README preview image
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.vue
        └── main.js
```

## API Overview

| Method | Endpoint | Auth Required | Description |
| --- | --- | --- | --- |
| `GET` | `/api/topics` | No | List saved topics |
| `GET` | `/api/stats` | No | Return dashboard statistics |
| `POST` | `/api/sync` | Yes | Start a background sync task |
| `GET` | `/api/sync/progress` | No | Poll sync progress |
| `POST` | `/api/admin/login` | No | Admin login |
| `POST` | `/api/admin/logout` | Yes | Admin logout |
| `GET` | `/api/admin/config` | Yes | Read masked LLM config |
| `POST` | `/api/admin/config` | Yes | Update LLM config or password |
| `GET` | `/api/admin/setup-status` | No | Check initial setup status |
| `POST` | `/api/admin/setup` | Yes | Complete first-run setup |

## Security Notes

- Change the default password immediately after deployment.
- Keep the LLM API key in the admin panel or deployment environment, not in committed source code.
- Manual synchronization and configuration endpoints require an admin bearer token.
- Public read-only endpoints expose saved topic data and dashboard statistics by design.

## License

No license has been specified yet. Add a license before publishing the repository if you want others to use or modify the code.
