# 🚀 Squirrel 快速启动指南

## 一键部署

### Linux / Mac
```bash
./deploy.sh
```

### Windows PowerShell
```powershell
.\deploy.ps1
```

就这么简单！脚本会自动完成所有配置和部署。

---

## 手动部署（3 步）

### 1️⃣ 创建配置文件

创建 `.env` 文件：
```bash
cat > .env << 'EOF'
REDIS_PASSWORD=squirrel123
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=squirrel
EOF
```

### 2️⃣ 启动服务

```bash
docker compose up -d
```

### 3️⃣ 访问应用

浏览器打开：**http://localhost:8000**

---

## 从源码构建

### 构建插件
```bash
./build_plugins.sh -d
```

### 构建镜像
```bash
./build.sh
```

### 启动服务
```bash
docker compose up -d
```

---

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

---

## 目录结构

```
.
├── config/          # 配置文件目录
├── logs/            # 日志文件目录
├── downloads/       # 下载文件目录
├── postgres/data/   # PostgreSQL 数据
├── redis/data/      # Redis 数据
└── .env             # 环境变量配置
```

---

## 下一步

1. **修改默认密码** - 编辑 `.env` 文件
2. **配置 Cookie** - 根据需要配置 Cookie Cloud
3. **安装浏览器扩展** - 方便订阅网站内容
4. **查看详细文档** - [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## 遇到问题？

- 📖 [部署指南](./DEPLOYMENT.md)
- 📋 [更新说明](./DEPLOYMENT_UPDATES.md)
- 💬 [提交 Issue](https://github.com/klaxonz/squirrel/issues)
- 📝 查看日志：`./logs/app.log`

