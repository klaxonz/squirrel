# Media Subscribe

Media Subscribe 是一个强大的视频下载和管理工具，专为 Emby / Jellyfin 媒体服务器设计。它可以下载视频并生成nfo文件，以便媒体服务器识别元数据。

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

## 快速开始

### 环境要求

- Python 3.11+
- pipenv
- Node.js 14+
- pnpm (用于前端依赖管理)
- Docker (可选，用于容器化部署)

### 安装步骤

1. **克隆项目**：
   ```bash
   git clone https://github.com/klaxonz/media-subscribe.git
   cd media-subscribe
   ```

2. **后端设置**：
   - 安装pipenv（如果尚未安装）：
     ```bash
     pip install pipenv
     ```
   - 创建并激活虚拟环境：
     ```bash
     pipenv --python 3.11
     pipenv shell
     ```
   - 安装Python依赖：
     ```bash
     pipenv install
     ```
   - 配置环境变量：复制 `.env.example` 为 `.env` 并按需填写

3. **前端设置**：
   - 安装pnpm（如果尚未安装）：
     ```bash
     npm install -g pnpm
     ```
   - 安装依赖并构建：
     ```bash
     cd media-subscribe-front
     pnpm install
     pnpm run build
     ```

4. **启动应用**：
   - 后端（确保在虚拟环境中）：
     ```bash
     python media-subscribe/main.py
     ```
   - 前端（开发模式）：
     ```bash
     pnpm run dev
     ```

### 使用指南

1. 访问Web界面：打开浏览器，访问 `http://localhost:5173`（或配置的其他地址）
2. 添加订阅：使用Web界面添加YouTube或Bilibili频道URL
3. 管理订阅：在订阅列表中查看和管理您的订阅
4. 浏览最新视频：在"最新视频"页面查看下载的内容
5. 使用浏览器拓展：在支持的网站上快速添加订阅
6. 配置设置：调整下载路径、更新频率等参数

### Docker部署

1. 构建镜像：
   ```bash
   ./build.sh
   ```
2. 运行容器：
   ```bash
   docker compose up -d
   ```

### 浏览器拓展安装

1. 安装浏览器插件
2. 打开浏览器，找到扩展管理，将 media-subscribe-extension 目录导入到浏览器拓展中

## 贡献

欢迎提交问题报告、功能请求和代码贡献。请查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解更多信息。

## 许可

本项目遵循 [MIT License](./LICENSE)。