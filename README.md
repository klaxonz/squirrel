# Media Subscribe

Media Subscribe 是一个下载视频，并生成nfo文件，以供 Emby / Jellyfin 媒体服务器元数据识别的下载器。
## 功能特性

- 支持网站：YouTube、Bilibili
- 订阅频道：支持订阅频道、并自动下载最新视频
- 油猴脚本：提供油猴脚本、方便网页端操作

## Todo
- [ ] 添加更多网站支持
- [ ] 增加 UI
- [ ] 增加下载参数配置
- [ ] 完善油猴脚本

## 快速开始

### 环境要求

- Python 3.11 +
- Docker (可选，用于容器化部署)

### 安装步骤

1. **克隆项目**：
```bash
git clone https://github.com/klaxonz/media-subscribe.git cd media-subscribe
```
2. **安装依赖**：
   使用Pipenv管理依赖（推荐）：
```bash
pip install pipenv
pipenv install --deploy
```

3. **配置环境变量**：
   复制`.env.example`为`.env`并根据需要填写环境变量。

4. **运行应用**：
   使用Pipenv：
```bash
pipenv run python media-subscribe/main.py
```

### 容器化部署
1. **构建镜像**：
```bash
./build.sh
```
2. **运行容器**：
```bash
docker compose up -d
```

### 安装油猴脚本
1. **安装油猴脚本浏览器插件**
2. **添加油猴脚本**： 在油猴脚本插件中新建一个脚本，将 media-subscribe-monkey/media-subscribe.user.js 代码拷贝进去，保存即可。

## 许可

本项目遵循[MIT License](./LICENSE)。