# Squirrel 部署指南

## 📋 部署前准备

### 1. 创建环境配置文件

在项目根目录创建 `.env` 文件，内容如下：

```env
# ========================================
# Redis 配置
# ========================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=squirrel123

# ========================================
# PostgreSQL 配置
# ========================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=squirrel

# ========================================
# 下载配置
# ========================================
MEDIA_DOWNLOAD_PATH=/downloads

# ========================================
# Cookie 配置
# ========================================
# Cookie 类型: file | cloud
COOKIE_TYPE=file

# Cookie Cloud 配置（当 COOKIE_TYPE=cloud 时使用）
COOKIE_CLOUD_URL=
COOKIE_CLOUD_UUID=
COOKIE_CLOUD_PASSWORD=
COOKIE_CLOUD_DOMAIN=

# ========================================
# 数据库连接池配置
# ========================================
POOL_SIZE=30
POOL_MAX_SIZE=60
POOL_RECYCLE=300

# ========================================
# 频道更新配置
# ========================================
CHANNEL_UPDATE_DEFAULT_SIZE=30

# ========================================
# 运行环境
# ========================================
# 环境: dev | prod
ENV=prod
```

### 2. 创建必要的目录

```bash
mkdir -p config logs downloads postgres/data redis/data
```

## 🔨 构建镜像

### 基础构建

```bash
# 仅构建应用镜像
./build.sh

# 构建基础镜像 + 应用镜像
./build.sh -b

# 不使用缓存重新构建
./build.sh --no-cache

# 跳过插件构建
./build.sh --skip-plugins
```

### 推送到仓库

```bash
# 构建并推送应用镜像
./build.sh -p

# 构建并推送基础镜像 + 应用镜像
./build.sh -b -p
```

### 多平台构建（需要推送）

```bash
# 构建多平台应用镜像 (linux/amd64, linux/arm64)
./build.sh -m -p

# 构建多平台基础镜像 + 应用镜像
./build.sh -b -m -p
```

### 查看帮助

```bash
./build.sh -h
```

## 🚀 启动服务

### 使用 Docker Compose

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

### 使用已构建的镜像

如果你已经构建了镜像，直接运行：

```bash
docker compose up -d
```

### 使用远程镜像

如果使用 Docker Hub 上的镜像，确保 `docker-compose.yaml` 中的镜像名称正确：

```yaml
services:
  squirrel:
    image: klaxonz/squirrel:latest
    # ...
```

## 📦 服务说明

### Squirrel 主服务

- **端口**: 8000
- **健康检查**: `http://localhost:8000/health`
- **数据卷**:
  - `./config:/app/config` - 配置文件
  - `./logs:/app/logs` - 日志文件
  - `./downloads:/downloads` - 下载的媒体文件
  - `./squirrel-backend/plugins_ext:/app/squirrel-backend/plugins_ext` - 插件目录

### Redis

- **端口**: 6379
- **数据卷**: `./redis/data:/data`
- **密码**: 通过环境变量 `REDIS_PASSWORD` 配置

### PostgreSQL

- **端口**: 5432
- **数据卷**: `./postgres/data:/var/lib/postgresql/data`
- **数据库**: 通过环境变量配置

## 🔍 健康检查

所有服务都配置了健康检查：

- **Squirrel**: 每30秒检查一次，启动40秒后开始
- **Redis**: 每5秒检查一次
- **PostgreSQL**: 每10秒检查一次

查看健康状态：

```bash
docker compose ps
```

## 🛠️ 故障排查

### 查看日志

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

## 🔄 更新部署

### 更新应用

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
./build.sh

# 3. 重启服务
docker compose down
docker compose up -d
```

### 仅更新插件

```bash
# 1. 构建插件
./build_plugins.sh -d

# 2. 重启 Squirrel 服务
docker compose restart squirrel
```

## 📊 访问应用

应用启动后，通过浏览器访问：

```
http://localhost:8000
```

## 🔐 安全建议

1. **修改默认密码**: 修改 `.env` 文件中的 `REDIS_PASSWORD` 和 `POSTGRES_PASSWORD`
2. **限制端口暴露**: 生产环境中，考虑只暴露必要的端口
3. **使用反向代理**: 建议使用 Nginx 或 Traefik 作为反向代理
4. **启用 HTTPS**: 配置 SSL 证书

## 🌐 反向代理配置示例（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📝 备份与恢复

### 备份数据

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

## 🆘 获取帮助

如遇到问题，请查看：

1. [项目 README](./README.md)
2. [GitHub Issues](https://github.com/klaxonz/squirrel/issues)
3. 日志文件: `./logs/app.log`

