# Squirrel

Squirrel 是一个视频订阅和下载工具，下载时可以生成nfo文件，以供 Emby / Jellyfin 识别元数据。

## 功能特性

- 多平台支持：目前支持 YouTube 和 Bilibili
- 频道订阅：自动下载订阅频道的最新视频
- 用户友好的Web界面：方便管理订阅和下载
- 桌面端壳：可直接以桌面应用方式承载现有界面
- 浏览器拓展：方便快捷的订阅站点频道
- 视频内容展示：轻松浏览和管理下载的内容
- 音乐搜索与播放：通过内置 KuGouMusicApi sidecar 提供酷狗音乐能力
- 定时更新：定时更新订阅频道视频

## 待办事项

- [ ] 扩展支持更多视频平台
- [ ] 实现可自定义的下载参数配置

## 目录

- [快速开始](#快速开始)
  - [完整部署](#方式一完整部署包含数据库和redis)
  - [独立部署](#方式二独立部署使用已有的数据库和redis)（使用已有的数据库和Redis）
- [详细部署指南](#详细部署指南)
- [常用命令](#常用命令)
- [浏览器扩展](#浏览器扩展)
- [桌面端](#桌面端)
- [插件开发](#插件开发)
- [故障排查](#故障排查)
- [备份与恢复](#备份与恢复)

## 快速开始

### 🚀 快速部署

`docker-compose.yaml` 支持两种部署模式，通过注释配置切换。

#### 方式一：完整部署（包含数据库和Redis）

1. 复制环境变量示例文件：
```bash
cp env.example .env
# 根据需要修改 .env 文件中的密码等配置
```

2. 启动服务：
```bash
docker compose up -d
```

Cloudflare bypass sidecar 和 KuGou music sidecar 现在也会随 compose 一起启动；容器内默认地址分别是 `http://squirrel-cf-bypass:8002`、`http://squirrel-music-api:3000`，宿主机默认端口分别是 `8002`、`8003`。如果在外部部署目录运行 compose，请确保同时准备好 `klaxonz/squirrel:latest`、`klaxonz/squirrel-cf-bypass:latest` 和 `klaxonz/squirrel-music-api:latest` 三个镜像。

3. 访问应用：`http://localhost:8001`

#### 方式二：独立部署（使用已有的数据库和Redis）

1. 复制并修改环境变量：
```bash
cp env.example .env
# 修改 .env 文件中的数据库和 Redis 连接信息：
# - REDIS_HOST=你的Redis地址
# - REDIS_PASSWORD=你的Redis密码
# - POSTGRES_HOST=你的PostgreSQL地址
# - POSTGRES_PASSWORD=你的PostgreSQL密码
```

2. 启动服务（仅启动 Squirrel，不启动数据库；如需本地 sidecar，一并启动）：
```bash
docker compose up -d --no-deps squirrel squirrel-cf-bypass squirrel-music-api
```

3. 访问应用：`http://localhost:8001`

**说明：** 
- `--no-deps` 参数会跳过依赖服务（Redis 和 PostgreSQL），不会拉取或启动它们
- 确保外部数据库可以从容器内访问（使用 `host.docker.internal` 或实际 IP）

### 使用指南

1. 添加订阅：使用Web界面添加YouTube或Bilibili频道URL
2. 管理订阅：在订阅列表中查看和管理您的订阅
3. 浏览最新视频：在"最新视频"页面查看下载的内容
4. 使用浏览器拓展：在支持的网站上快速添加订阅
5. 配置设置：调整下载路径、更新频率等参数

## 详细部署指南

### 📋 部署配置说明

#### 环境变量配置

```bash
# 复制示例文件
cp env.example .env

# 完整部署：保持默认配置即可
# 独立部署：修改以下配置
# - REDIS_HOST: 改为外部 Redis 地址
# - REDIS_PASSWORD: 改为实际密码
# - POSTGRES_HOST: 改为外部 PostgreSQL 地址
# - POSTGRES_PASSWORD: 改为实际密码
```

#### Docker Compose 独立部署配置

独立部署时使用 `--no-deps` 参数跳过数据库服务：

```bash
# 修改 .env 文件配置外部数据库连接信息

# 启动服务（不启动 Redis 和 PostgreSQL）
docker compose up -d --no-deps squirrel
```

#### 创建必要的目录

```bash
# 完整部署：需要数据库数据目录
mkdir -p config logs downloads postgres/data redis/data

# 独立部署：不需要数据库数据目录
mkdir -p config logs downloads thumbnails
```

### 📦 Docker Compose 使用

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f squirrel

# 停止服务
docker compose down

# 停止服务并删除数据卷
docker compose down -v
```

- `squirrel-cf-bypass` 负责 backend 的 Cloudflare bypass 请求。
- 容器部署时 `CLOUDFLARE_BYPASS_SERVICE_URL` 应指向 `http://squirrel-cf-bypass:8002`。
- `squirrel-music-api` 负责 backend 的酷狗音乐搜索和播放地址解析请求。
- 容器部署时 `KUGOU_MUSIC_API_BASE_URL` 应指向 `http://squirrel-music-api:3000`。
- 外部部署目录运行 compose 时，需要单独提供 `klaxonz/squirrel-cf-bypass:latest` 和 `klaxonz/squirrel-music-api:latest` 镜像，而不是依赖本地 sidecar 构建上下文。

### 📊 服务说明

#### Squirrel 主服务

- **端口**: `PORT`（默认 `8001`，宿主机与容器内保持一致）
- **健康检查**: `http://localhost:8001/health`
- **数据卷**:
  - `./config:/app/config` - 配置文件
  - `./logs:/app/logs` - 日志文件
  - `./downloads:/downloads` - 下载的媒体文件

#### Cloudflare bypass sidecar

- **端口**: `CF_BYPASS_PORT`（默认 `8002`，宿主机与容器内保持一致）
- **容器内地址**: `http://squirrel-cf-bypass:8002`

#### KuGou music sidecar

- **端口**: `KUGOU_MUSIC_API_PORT`（默认 `8003`，容器内固定为 `3000`）
- **容器内地址**: `http://squirrel-music-api:3000`
- **认证 Cookie**: `KUGOU_MUSIC_COOKIE`，部分酷狗接口需要 `token/userid/dfid`

#### Redis

- **端口**: 6379
- **数据卷**: `./redis/data:/data`
- **密码**: 通过环境变量 `REDIS_PASSWORD` 配置

#### PostgreSQL

- **端口**: 5432
- **数据卷**: `./postgres/data:/var/lib/postgresql/data`
- **数据库**: 通过环境变量配置

### 🔍 健康检查

所有服务都配置了健康检查：

- **Squirrel**: 每30秒检查一次，启动40秒后开始
- **Redis**: 每5秒检查一次
- **PostgreSQL**: 每10秒检查一次

查看健康状态：

```bash
docker compose ps
```

### 🔄 更新部署

```bash
# 1. 拉取最新代码
git pull

# 2. 重启服务
docker compose down
docker compose up -d
```

**说明：**
- 完整部署：直接更新即可
- 独立部署：`docker-compose.override.yaml` 不会被 git 跟踪，您的配置不会丢失

## 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f squirrel

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 进入容器
docker compose exec squirrel bash

# 健康检查
curl http://localhost:8001/health
```

### 目录结构

```
.
├── config/          # 配置文件目录
├── logs/            # 日志文件目录
├── downloads/       # 下载文件目录
├── postgres/data/   # PostgreSQL 数据
├── redis/data/      # Redis 数据
└── .env             # 环境变量配置
```

## 浏览器扩展

### 安装步骤

1. 安装浏览器插件
2. 打开浏览器，找到扩展管理
3. 将 `squirrel-extension` 目录导入到浏览器扩展中

## 桌面端

仓库提供了独立的 `squirrel-desktop` Electron 子项目，用来承载现有 Web UI。

```bash
cd squirrel-desktop
npm install
npm run dev
```

- `npm run dev` 会启动桌面壳，并自动联动 `squirrel-frontend` 开发服务器。
- 默认要求后端运行在 `http://127.0.0.1:8001`。
- 打包可使用 `npm run build` 或 `npm run dist`。

## 插件开发

Squirrel 支持通过插件系统扩展更多视频平台。

### 插件目录

- `squirrel-plugins/` - 插件源码目录
  - `bilibili/` - Bilibili 插件
  - `youtube/` - YouTube 插件
  - `javdb/` - JavDB 插件
  - `pornhub/` - PornHub 插件

## 故障排查

### 🛠️ 查看日志

```bash
# 所有服务日志
docker compose logs -f

# Squirrel 服务日志
docker compose logs -f squirrel

# Redis 日志
docker compose logs -f redis

# PostgreSQL 日志
docker compose logs -f postgres
```

### 重启服务

```bash
# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart squirrel
```

### 进入容器

```bash
# 进入 Squirrel 容器
docker compose exec squirrel bash

# 进入 PostgreSQL 容器
docker compose exec postgres bash

# 进入 Redis 容器
docker compose exec redis sh
```

### 检查数据库连接

```bash
# 在 Squirrel 容器中测试数据库连接
docker compose exec squirrel python -c "from core.config import settings; print(settings.database_url)"
```

## 备份与恢复

### 📝 备份数据

```bash
# 备份 PostgreSQL 数据库
docker compose exec postgres pg_dump -U postgres squirrel > backup.sql

# 备份配置和数据
tar -czf squirrel-backup-$(date +%Y%m%d).tar.gz config downloads postgres/data redis/data
```

### 恢复数据

```bash
# 恢复 PostgreSQL 数据库
cat backup.sql | docker compose exec -T postgres psql -U postgres squirrel

# 恢复配置和数据
tar -xzf squirrel-backup-YYYYMMDD.tar.gz
```

## 🔐 安全建议

1. **修改默认密码**: 修改 `.env` 文件中的 `REDIS_PASSWORD` 和 `POSTGRES_PASSWORD`
2. **限制端口暴露**: 生产环境中，考虑只暴露必要的端口
3. **使用反向代理**: 建议使用 Nginx 或 Traefik 作为反向代理
4. **启用 HTTPS**: 配置 SSL 证书

### 🌐 反向代理配置示例（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🆘 获取帮助

如遇到问题，请查看：

1. 日志文件: `./logs/app.log`
2. [GitHub Issues](https://github.com/klaxonz/squirrel/issues)
3. 提交问题反馈

## 贡献

欢迎提交问题报告、功能请求和代码贡献。请查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解更多信息。

## 许可

本项目遵循 [MIT License](./LICENSE)。
