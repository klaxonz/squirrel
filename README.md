# Squirrel（归仓）

自托管的多站视频订阅中枢。跨站点订阅并同步到本地库，在同一处浏览、整理与播放。

| | |
|--|--|
| **主路径** | 订阅 → 同步入库 → 浏览 / 未读 / 稍后看 → 播放 |
| **支撑** | 站点会话、定时任务、日志 |
| **形态** | 后端 API + 桌面端（Electron）+ 浏览器扩展 |

数据与配置在你自己的环境里。UI 仅维护在桌面端；站点登录、远端搜索与播流解析由 Electron 主进程提供。

## 能力概览

- **多站订阅与同步** — 频道订阅、导入、定时/手动同步。站点实现在 `squirrel-backend/sites/`（in-tree 模块），开关与参数在 `config/sites.json`（含 YouTube、Bilibili 等）。
- **内容库** — 首页推荐、视频库（全部 / 未读 / 已读 / 稍后看 / 喜欢）、历史、播放列表。
- **播放** — 应用内播放；桌面端可按站点会话解析地址与字幕。
- **桌面增强** — 站点登录与 cookie、远端搜索、远端频道浏览。
- **扩展** — 浏览器扩展一键加订；RSS 阅读；酷狗音乐（桌面）。
- **运维** — 站点连通性、计划任务、日志、系统设置。

## 仓库结构

```
squirrel-backend/       API、同步与抽取、调度；站点实现在 sites/ 下（crawl + squirrel_youtube + squirrel_bilibili）
squirrel-desktop/       Electron 桌面端（main + renderer UI）
squirrel-extension/     浏览器扩展
squirrel-cf-bypass/     Cloudflare bypass sidecar
config/                 站点与运行配置（部署时挂载）
```

## 快速开始

需要 Docker 与 Docker Compose。默认镜像：`klaxonz/squirrel:latest`、`klaxonz/squirrel-cf-bypass:latest`。

### 1. 完整部署（自带 Postgres / Redis / Meilisearch）

```bash
cp env.example .env
# 至少修改 JWT_SECRET_KEY、REDIS_PASSWORD、POSTGRES_PASSWORD

mkdir -p config logs downloads thumbnails postgres/data redis/data
docker compose up -d
```

健康检查：`curl http://localhost:8001/health`（API；UI 在桌面端）

默认会拉起：

| 服务 | 作用 | 默认端口 |
|------|------|----------|
| `squirrel` | API | `8001` |
| `squirrel-worker` | 消息与后台任务 | — |
| `squirrel-scheduler` | 定时与 crawl 调度 | — |
| `squirrel-cf-bypass` | Cloudflare bypass | `8002` |
| `postgres` / `redis` / `meilisearch` | 数据与搜索 | 内网 |

### 2. 接入已有数据库

1. 编辑 `.env`，将 `REDIS_HOST`、`POSTGRES_HOST` 及对应密码改成外部实例（本机 Docker Desktop 常用 `host.docker.internal`）。
2. 只启动应用进程（不拉起 compose 内的 DB）：

```bash
docker compose up -d --no-deps \
  squirrel squirrel-worker squirrel-scheduler squirrel-cf-bypass
```

确保容器能访问外部 Postgres / Redis；若搜索也外置，需同步调整 Meilisearch 相关配置。

### 3. 用起来

1. 启动桌面端（`npm run dev:desktop` 或安装包），连接本机 API（默认 `http://127.0.0.1:8001`），注册/登录。
2. 在「订阅」添加频道 URL，或用浏览器扩展在站点页加订。
3. 等待定时同步，或在界面中手动刷新。
4. 在首页 / 视频库浏览，用未读、稍后看等整理；点开即可播放。
5. 站点登录、远端搜索与播流解析在桌面端完成。
6. 同步异常时看「站点」「定时」「日志」。

## 配置要点

复制 `env.example` 为 `.env`。常用项：

| 变量 | 说明 |
|------|------|
| `PORT` | Web 端口，默认 `8001` |
| `CF_BYPASS_PORT` | bypass 端口，默认 `8002` |
| `CLOUDFLARE_BYPASS_SERVICE_URL` | 容器内一般为 `http://squirrel-cf-bypass:8002` |
| `REDIS_*` / `POSTGRES_*` | 缓存与数据库 |
| `JWT_SECRET_KEY` | 生产环境务必改为长随机串 |
| `THUMBNAILS_DIR` | 缩略图宿主机目录 |
| `COOKIECLOUD_*` | 可选，CookieCloud 同步 |

站点启用与元数据：`config/sites.json`。

数据卷（主服务）：

- `./config` → `/app/config`
- `./logs` → `/app/logs`
- `./downloads` → `/downloads`
- `./thumbnails`（或 `THUMBNAILS_DIR`）→ `/thumbnails`

## 常用命令

```bash
docker compose ps
docker compose logs -f squirrel
docker compose logs -f squirrel-worker
docker compose restart squirrel
docker compose down

# 更新镜像后
docker compose pull
docker compose up -d
```

## 桌面端

UI 在 `squirrel-desktop/renderer/`，与 Electron 主进程同包维护。

```bash
# 仓库根目录
npm install
npm run dev:desktop   # Vite renderer + Electron；后端默认 http://127.0.0.1:8001

# 或
cd squirrel-desktop
npm run dev           # 开发
npm run build:renderer
npm run build         # UI + unpacked
npm run dist          # 安装包
```

### 质量门

根目录脚本聚合桌面端的日常检查：

```bash
npm install
npm run lint
npm run typecheck
npm test
npm run build
npm run check
```

后端检查在 `squirrel-backend/` 中执行：`pipenv sync --dev`、`pipenv run pytest`、`pipenv run ruff check .` 与 `pipenv run python -m compileall -q .`。CI 会在干净环境中运行这些检查。

Electron smoke 测试需要本地 ChromeDriver 与 Electron 二进制可用，命令为 `cd squirrel-desktop && npm run test:electron`；环境不具备时该可选 CI job 会保留失败产物并标记为允许失败。

环境变量见 `squirrel-desktop/README.md`（`DESKTOP_RENDERER_URL`、`VITE_BACKEND_URL` 等）。

## 浏览器扩展

1. 打开浏览器扩展管理，启用「开发者模式」。
2. 「加载已解压的扩展程序」，选择仓库中的 `squirrel-extension/`。
3. 在扩展选项里配置 Squirrel 服务地址后，在支持的站点页加订。

## 站点集成

站点集成为 backend 内的 first-party 模块，进程内直接调用，不接受上传安装包。

- 站点源码：`squirrel-backend/sites/squirrel_youtube/`、`squirrel-backend/sites/squirrel_bilibili/`
- 共用接口层：`squirrel-backend/sites/crawl/`（协议、HTTP、异常、抓取基类）
- 启用与域名等：`config/sites.json`（合并站点默认元数据）
- 能力（每个站点对象上的类型化方法）：`extract_video`、`sync_subscription`、`import_subscriptions`、`resolve_subscription`、`check_login_status`

开发说明见 `squirrel-backend/README.md` 与 `sites/` 目录。

## 备份

```bash
# 数据库
docker compose exec postgres pg_dump -U postgres squirrel > backup.sql

# 配置与卷（按你实际保留的目录调整）
tar -czf squirrel-backup-$(date +%Y%m%d).tar.gz config logs downloads thumbnails postgres/data redis/data
```

恢复示例：

```bash
cat backup.sql | docker compose exec -T postgres psql -U postgres squirrel
tar -xzf squirrel-backup-YYYYMMDD.tar.gz
```

## 故障排查

| 现象 | 建议 |
|------|------|
| 服务起不来 | `docker compose ps`，再看对应服务 `logs` |
| API 不通 | `curl http://localhost:8001/health`；检查 `PORT` 与反向代理 |
| 同步失败 | 查「日志」、站点是否需登录/cookie、`squirrel-worker` / `squirrel-scheduler` 是否在跑 |
| CF 相关失败 | 确认 `squirrel-cf-bypass` healthy，且 `CLOUDFLARE_BYPASS_SERVICE_URL` 正确 |
| 数据库连不上 | 核对 `.env` 主机名；独立部署时应用容器能否解析外部 DB |

应用日志目录：`./logs/`（如 `app.log`）。

## 安全

- 修改默认 `REDIS_PASSWORD`、`POSTGRES_PASSWORD`、`JWT_SECRET_KEY`。
- 生产环境不要把数据库端口暴露到公网；Web 建议置于反向代理之后并启用 HTTPS。

Nginx 示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 许可

[MIT License](./LICENSE)

问题与反馈：[GitHub Issues](https://github.com/klaxonz/squirrel/issues)
