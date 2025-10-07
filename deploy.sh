#!/bin/bash

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示欢迎信息
echo -e "${GREEN}"
cat << "EOF"
 ____              _                _ 
/ ___|  __ _ _   _(_)_ __ _ __ ___| |
\___ \ / _` | | | | | '__| '__/ _ \ |
 ___) | (_| | |_| | | |  | | |  __/ |
|____/ \__, |\__,_|_|_|  |_|  \___|_|
          |_|                        
EOF
echo -e "${NC}"
echo -e "${BLUE}Squirrel 快速部署脚本${NC}"
echo -e "${BLUE}========================${NC}"
echo ""

# 检查 Docker 和 Docker Compose
check_requirements() {
    echo -e "${YELLOW}[1/5] 检查环境依赖...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: 未找到 Docker，请先安装 Docker${NC}"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}错误: 未找到 Docker Compose，请先安装 Docker Compose${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Docker 和 Docker Compose 已安装${NC}"
}

# 创建环境配置文件
create_env_file() {
    echo -e "${YELLOW}[2/5] 创建环境配置文件...${NC}"
    
    if [ -f ".env" ]; then
        echo -e "${YELLOW}⚠ .env 文件已存在，跳过创建${NC}"
        return
    fi
    
    cat > .env << 'EOF'
# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=squirrel123

# PostgreSQL 配置
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=squirrel

# 下载配置
MEDIA_DOWNLOAD_PATH=/downloads

# Cookie 配置
COOKIE_TYPE=file
COOKIE_CLOUD_URL=
COOKIE_CLOUD_UUID=
COOKIE_CLOUD_PASSWORD=
COOKIE_CLOUD_DOMAIN=

# 数据库连接池配置
POOL_SIZE=30
POOL_MAX_SIZE=60
POOL_RECYCLE=300

# 频道更新配置
CHANNEL_UPDATE_DEFAULT_SIZE=30

# 运行环境
ENV=prod
EOF
    
    echo -e "${GREEN}✓ .env 文件创建成功${NC}"
    echo -e "${YELLOW}提示: 请根据需要修改 .env 文件中的配置${NC}"
}

# 创建必要的目录
create_directories() {
    echo -e "${YELLOW}[3/5] 创建必要的目录...${NC}"
    
    mkdir -p config logs downloads postgres/data redis/data
    chmod -R 755 config logs downloads postgres/data redis/data
    
    echo -e "${GREEN}✓ 目录创建成功${NC}"
}

# 构建或拉取镜像
setup_images() {
    echo -e "${YELLOW}[4/5] 准备 Docker 镜像...${NC}"
    
    read -p "是否从源码构建镜像？(y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}开始构建镜像...${NC}"
        if [ -f "./build.sh" ]; then
            chmod +x ./build.sh
            ./build.sh
        else
            echo -e "${RED}错误: 未找到 build.sh 脚本${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}从 Docker Hub 拉取镜像...${NC}"
        docker compose pull
    fi
    
    echo -e "${GREEN}✓ 镜像准备完成${NC}"
}

# 启动服务
start_services() {
    echo -e "${YELLOW}[5/5] 启动服务...${NC}"
    
    docker compose up -d
    
    echo -e "${GREEN}✓ 服务启动成功${NC}"
}

# 显示部署结果
show_result() {
    echo ""
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}部署完成！${NC}"
    echo -e "${GREEN}=====================================${NC}"
    echo ""
    
    # 等待几秒让服务启动
    echo -e "${YELLOW}等待服务启动...${NC}"
    sleep 5
    
    # 显示服务状态
    echo -e "${BLUE}服务状态:${NC}"
    docker compose ps
    
    echo ""
    echo -e "${BLUE}访问地址:${NC}"
    echo -e "  ${GREEN}http://localhost:8000${NC}"
    echo ""
    
    echo -e "${BLUE}常用命令:${NC}"
    echo -e "  查看日志: ${YELLOW}docker compose logs -f${NC}"
    echo -e "  停止服务: ${YELLOW}docker compose down${NC}"
    echo -e "  重启服务: ${YELLOW}docker compose restart${NC}"
    echo ""
    
    echo -e "${BLUE}配置文件位置:${NC}"
    echo -e "  环境配置: ${YELLOW}.env${NC}"
    echo -e "  应用配置: ${YELLOW}./config/${NC}"
    echo -e "  日志文件: ${YELLOW}./logs/${NC}"
    echo -e "  下载目录: ${YELLOW}./downloads/${NC}"
    echo ""
    
    echo -e "${YELLOW}提示: 首次启动可能需要等待数据库初始化，请稍候${NC}"
}

# 主流程
main() {
    check_requirements
    create_env_file
    create_directories
    setup_images
    start_services
    show_result
}

# 执行主流程
main

