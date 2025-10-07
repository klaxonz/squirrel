# Squirrel

Squirrel 是一个视频订阅和下载工具，下载时可以生成nfo文件，以供 Emby / Jellyfin 识别元数据。

## 功能特性

- 多平台支持：目前支持 YouTube 和 Bilibili
- 频道订阅：自动下载订阅频道的最新视频
- 用户友好的Web界面：方便管理订阅和下载
- 浏览器拓展：方便快捷的订阅站点频道
- 视频内容展示：轻松浏览和管理下载的内容
- 定时更新：定时更新订阅频道视频

## 待办事项

- [ ] 扩展支持更多视频平台
- [ ] 实现可自定义的下载参数配置

## 目录

- [快速开始](#快速开始)
  - [一键部署](#一键部署推荐)
  - [手动部署](#手动部署3步)
- [详细部署指南](#详细部署指南)
  - [完整部署配置](#完整部署配置)
  - [独立部署配置](#独立部署配置)（使用已有的数据库和Redis）
- [常用命令](#常用命令)
- [浏览器扩展](#浏览器扩展)
- [插件开发](#插件开发)
- [故障排查](#故障排查)
- [备份与恢复](#备份与恢复)

## 快速开始

### 🚀 一键部署（推荐）

**Linux/Mac:**
```bash
./deploy.sh
```

**Windows PowerShell:**
```powershell
.\deploy.ps1
```

部署脚本支持两种模式：
- **完整部署**：自动部署 Squirrel、PostgreSQL 和 Redis
- **独立部署**：仅部署 Squirrel，使用已有的 PostgreSQL 和 Redis

脚本会自动：
- 选择部署模式
- 检查 Docker 环境
- 创建 `.env` 配置文件
- 创建必要的目录
- 拉取或构建镜像
- 启动服务

**独立部署说明：**
- 选择独立部署时，脚本会提示输入外部数据库和 Redis 的连接信息
- 默认使用 `host.docker.internal` 连接宿主机服务（适用于 Docker Desktop）
- Linux 用户可能需要使用宿主机 IP（如 `172.17.0.1`）

### 📦 手动部署（3步）

**方式一：完整部署（包含数据库和Redis）**

1. 复制环境变量示例文件：
```bash
cp env.example .env
# 根据需要修改 .env 文件中的密码等配置
```

2. 启动服务：
```bash
docker compose up -d
```

3. 访问应用：`http://localhost:8000`

**方式二：独立部署（使用已有的数据库和Redis）**

如果您已经搭建好了 PostgreSQL 和 Redis：

1. 复制环境变量示例文件并修改：
```bash
cp env.example .env
# 根据 .env 文件中的注释修改数据库和 Redis 连接信息
```

2. 启动服务：
```bash
docker compose -f docker-compose.standalone.yaml up -d
```

3. 访问应用：`http://localhost:8000`

详细配置说明请参考 [独立部署配置](#独立部署配置)

### 使用指南

1. 添加订阅：使用Web界面添加YouTube或Bilibili频道URL
2. 管理订阅：在订阅列表中查看和管理您的订阅
3. 浏览最新视频：在"最新视频"页面查看下载的内容
4. 使用浏览器拓展：在支持的网站上快速添加订阅
5. 配置设置：调整下载路径、更新频率等参数

## 详细部署指南

### 📋 完整部署配置

适用于从零开始部署所有服务（包括 PostgreSQL 和 Redis）。

#### 1. 创建环境配置文件

```bash
# 复制示例文件
cp env.example .env

# 修改配置（可选）
# 建议修改：REDIS_PASSWORD、POSTGRES_PASSWORD
```

#### 2. 创建必要的目录

```bash
mkdir -p config logs downloads postgres/data redis/data
```

### 🔨 从源码构建

#### 构建插件

```bash
# 开发模式（自动部署到 plugins_ext 目录）
./build_plugins.sh -d

# 生产模式（仅打包到 plugin_packages 目录）
./build_plugins.sh
```

#### 构建镜像

**基础构建：**
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

**推送到仓库：**
```bash
# 构建并推送应用镜像
./build.sh -p

# 构建并推送基础镜像 + 应用镜像
./build.sh -b -p
```

**多平台构建（需要推送）：**
```bash
# 构建多平台应用镜像 (linux/amd64, linux/arm64)
./build.sh -m -p

# 构建多平台基础镜像 + 应用镜像
./build.sh -b -m -p
```

**查看帮助：**
```bash
./build.sh -h
```

#### 启动服务

```bash
docker compose up -d
```

### 📦 使用Docker Compose

#### 启动和停止

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

#### 使用远程镜像

如果使用 Docker Hub 上的镜像，确保 `docker-compose.yaml` 中的镜像名称正确：

```yaml
services:
  squirrel:
    image: klaxonz/squirrel:latest
    # ...
```

### 📊 服务说明

#### Squirrel 主服务

- **端口**: 8000
- **健康检查**: `http://localhost:8000/health`
- **数据卷**:
  - `./config:/app/config` - 配置文件
  - `./logs:/app/logs` - 日志文件
  - `./downloads:/downloads` - 下载的媒体文件
  - `./squirrel-backend/plugins_ext:/app/squirrel-backend/plugins_ext` - 插件目录

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

#### 更新应用

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
./build.sh

# 3. 重启服务
docker compose down
docker compose up -d
```

#### 仅更新插件

```bash
# 1. 构建插件
./build_plugins.sh -d

# 2. 重启 Squirrel 服务
docker compose restart squirrel
```

### 📋 独立部署配置

适用于已经搭建好 PostgreSQL 和 Redis 的场景。

#### 1. 准备外部服务

确保您已经有以下服务运行：
- **PostgreSQL** (推荐 15+)
- **Redis** (推荐 7+)

#### 2. 创建数据库

在 PostgreSQL 中创建 squirrel 数据库：

```sql
CREATE DATABASE squirrel;
```

#### 3. 配置环境变量

```bash
# 复制示例文件
cp env.example .env

# 根据 .env 文件中的注释修改数据库和 Redis 连接信息
# 必须修改：REDIS_HOST、REDIS_PASSWORD、POSTGRES_HOST、POSTGRES_PASSWORD
```

#### 4. 创建必要的目录

```bash
mkdir -p config logs downloads plugins_ext
```

#### 5. 启动服务

使用独立版 docker-compose 文件启动：

```bash
docker compose -f docker-compose.standalone.yaml up -d
```

#### 6. 查看日志

```bash
docker compose -f docker-compose.standalone.yaml logs -f
```

#### 7. 访问应用

浏览器访问：`http://localhost:8000`

#### 高级配置

**网络配置**

如果您的 Redis/PostgreSQL 在其他 Docker 容器中运行，可以让 Squirrel 加入同一网络：

```yaml
# 在 docker-compose.standalone.yaml 中修改
networks:
  squirrel-network:
    external: true
    name: your-existing-network
```

#### 独立部署常用命令

```bash
# 启动服务
docker compose -f docker-compose.standalone.yaml up -d

# 停止服务
docker compose -f docker-compose.standalone.yaml down

# 查看日志
docker compose -f docker-compose.standalone.yaml logs -f squirrel

# 重启服务
docker compose -f docker-compose.standalone.yaml restart

# 进入容器
docker compose -f docker-compose.standalone.yaml exec squirrel bash
```

#### 独立部署故障排查

**连接数据库失败：**

1. 检查数据库地址是否正确
   ```bash
   # 在容器中测试连接
   docker compose -f docker-compose.standalone.yaml exec squirrel bash
   ping $POSTGRES_HOST
   ```

2. 检查数据库是否允许远程连接
   - PostgreSQL: 修改 `postgresql.conf` 的 `listen_addresses`
   - PostgreSQL: 修改 `pg_hba.conf` 添加允许的IP段

3. 检查防火墙设置
   ```bash
   # 确保数据库端口可访问
   telnet POSTGRES_HOST 5432
   ```

**连接 Redis 失败：**

1. 检查 Redis 配置
   - 确保 Redis 绑定了正确的网络接口（`bind` 配置）
   - 检查 `protected-mode` 设置

2. 验证密码
   ```bash
   redis-cli -h REDIS_HOST -p 6379 -a your_password ping
   ```

**查看容器内配置：**

```bash
docker compose -f docker-compose.standalone.yaml exec squirrel env | grep -E '(REDIS|POSTGRES)'
```

#### 性能优化建议

**PostgreSQL 连接池配置：**

根据您的数据库性能调整连接池大小：

```env
# 基础连接池大小
POOL_SIZE=30

# 最大连接数
POOL_MAX_SIZE=60

# 连接回收时间（秒）
POOL_RECYCLE=300
```

**Redis 配置：**

确保 Redis 有足够的内存和适当的淘汰策略：

```redis
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

#### 从完整版迁移到独立版

1. 备份数据
   ```bash
   docker compose exec postgres pg_dump -U postgres squirrel > backup.sql
   ```

2. 导入到外部数据库
   ```bash
   psql -h YOUR_POSTGRES_HOST -U postgres squirrel < backup.sql
   ```

3. 迁移 Redis 数据（如需要）
   ```bash
   # 导出
   docker compose exec redis redis-cli -a squirrel123 --rdb dump.rdb
   
   # 导入到外部 Redis
   redis-cli -h YOUR_REDIS_HOST -a your_password --rdb dump.rdb
   ```

4. 切换到独立版部署
   ```bash
   docker compose down
   docker compose -f docker-compose.standalone.yaml up -d
   ```

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
curl http://localhost:8000/health
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

## 插件开发

Squirrel 支持通过插件系统扩展更多视频平台。

### 构建插件

使用 `build_plugins.sh` 脚本可以一键构建所有插件：

**生产模式**（仅打包插件）：
```bash
./build_plugins.sh
```
生成的插件包将保存在 `plugin_packages/` 目录，可通过 Web 界面上传安装。

**开发模式**（打包 + 自动部署）：
```bash
./build_plugins.sh -d
# 或
./build_plugins.sh --dev
```
开发模式下会自动将插件解压到 `squirrel-backend/plugins_ext/` 目录，无需手动上传。

**查看帮助**：
```bash
./build_plugins.sh -h
```

### 插件目录

- `squirrel-plugins/` - 插件源码目录
  - `bilibili/` - Bilibili 插件
  - `youtube/` - YouTube 插件
  - `javdb/` - JavDB 插件
  - `pornhub/` - PornHub 插件
- `plugin_packages/` - 构建产物（zip 包）
- `squirrel-backend/plugins_ext/` - 插件运行时目录

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
        proxy_pass http://localhost:8000;
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