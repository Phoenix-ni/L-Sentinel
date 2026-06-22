# linux.do 中转与公益站监控系统

一个面向 [linux.do](https://linux.do/) 论坛的帖子监控与 AI 筛选看板。系统会抓取最新主题，先用本地关键词做粗筛，再调用大语言模型进行语义分类、摘要和价值评分，适合追踪中转站、公益 API、福利优惠和服务异常状态等信息。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-42B883?logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

## Preview

![Dashboard preview](./粘贴的图像.png)

## Features

- 增量抓取 `linux.do/latest.json`，支持按最近 N 小时收集帖子。
- 自动跳过已入库帖子，减少重复处理和 LLM 调用成本。
- 本地关键词粗筛 + LLM 语义精筛，输出分类、摘要、相关性和 1-5 分价值评分。
- 支持 OpenAI 兼容协议与 Anthropic 协议，可在管理界面动态配置。
- FastAPI 提供帖子列表、统计数据、后台同步、同步进度和管理员配置接口。
- Vue 3 前端提供监控看板、系统配置、手动同步和数据概览。
- APScheduler 每天 08:00 自动抓取过去 24 小时的增量帖子。
- 默认使用 SQLite，也可通过 `DATABASE_URL` 切换到 MySQL / TiDB Serverless。
- Docker 多阶段构建，后端可直接托管构建后的前端静态资源。

## Tech Stack

| Layer | Stack |
| --- | --- |
| Frontend | Vue 3, Vite, Axios |
| Backend | FastAPI, Uvicorn, Pydantic |
| Data | SQLAlchemy, SQLite, MySQL / TiDB |
| Jobs | APScheduler |
| Crawler | `curl_cffi` / `requests` |
| LLM | OpenAI-compatible API, Anthropic API |
| Deployment | Docker, Render-compatible |

## Quick Start

### 1. Backend

```bash
pip install -r requirements.txt
uvicorn server:app --reload --port 8501
```

The backend runs at `http://localhost:8501`. On first start it creates the database tables automatically.

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

On first use, the app will require you to:

- change the admin password to a stronger password;
- configure the LLM provider, API key, base URL and model name.

## Configuration

Runtime configuration is stored in the database and can be updated from the admin panel.

| Config | Description |
| --- | --- |
| `ADMIN_PASSWORD` | Optional initial admin password or cloud password reset value |
| `DATABASE_URL` | Optional database URL; defaults to local SQLite `data.db` |
| LLM provider | `openai` or `anthropic` |
| LLM API key | Stored in database after setup |
| LLM base URL | Supports official endpoints or compatible gateways |
| LLM model | Model used for semantic filtering |

For public repositories, do not commit real API keys, database URLs, cookies or proxy credentials.

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

- If `DATABASE_URL` starts with `mysql://`, the app rewrites it to `mysql+pymysql://`.
- If the platform sleeps idle containers, use an external uptime monitor to request `/api/stats` periodically so the scheduler can keep running.
- The daily scheduled job uses the `Asia/Shanghai` timezone and runs at 08:00.

## CLI Usage

You can run the collection pipeline without starting the web server:

```bash
python main.py --hours 24
```

This fetches topics active in the last 24 hours, filters them and writes results to the configured database.

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

| Method | Endpoint | Auth | Description |
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
