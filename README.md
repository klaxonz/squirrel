# Media Subscribe

Media Subscribe 是一个旨在管理媒体订阅、通知和自动化处理的后台服务
## 功能特性

- **媒体处理**：集成FFmpeg，支持视频转码、剪辑等多媒体处理任务。
- **容器化部署**：Docker支持，简化部署流程。

## 快速开始

### 环境要求

- Python 3.9+
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

## 许可

本项目遵循[MIT License](./LICENSE)。