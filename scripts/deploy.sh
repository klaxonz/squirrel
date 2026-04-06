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

COMPOSE_FILE="docker-compose.yaml"

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
    
    # 复制示例文件
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${GREEN}✓ .env 文件创建成功（已从 env.example 复制）${NC}"
        
        echo -e "${YELLOW}提示：部署前请检查 .env 中的密码、缩略图路径和 Cloudflare 服务地址${NC}"
    else
        echo -e "${RED}错误: 未找到 env.example 文件${NC}"
        exit 1
    fi
}

# 创建必要的目录
create_directories() {
    echo -e "${YELLOW}[3/5] 创建必要的目录...${NC}"
    mkdir -p config logs downloads thumbnails postgres/data redis/data
    chmod -R 755 config logs downloads thumbnails postgres/data redis/data
    
    echo -e "${GREEN}✓ 目录创建成功${NC}"
}

# 构建或拉取镜像
setup_images() {
    echo -e "${YELLOW}[4/5] 准备 Docker 镜像...${NC}"
    
    read -p "是否从源码构建镜像？(y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}开始构建镜像...${NC}"
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [ -f "$SCRIPT_DIR/build.sh" ]; then
            chmod +x "$SCRIPT_DIR/build.sh"
            "$SCRIPT_DIR/build.sh"
        else
            echo -e "${RED}错误: 未找到 build.sh 脚本${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}从 Docker Hub 拉取镜像...${NC}"
        docker compose -f "$COMPOSE_FILE" pull
    fi
    
    echo -e "${GREEN}✓ 镜像准备完成${NC}"
}

# 启动服务
start_services() {
    echo -e "${YELLOW}[5/5] 启动服务...${NC}"
    
    docker compose -f "$COMPOSE_FILE" up -d
    
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
    docker compose -f "$COMPOSE_FILE" ps
    
    echo ""
    echo -e "${BLUE}访问地址:${NC}"
    echo -e "  ${GREEN}http://localhost:8001${NC}"
    echo ""
    
    echo -e "${BLUE}常用命令:${NC}"
    echo -e "  查看日志: ${YELLOW}docker compose -f $COMPOSE_FILE logs -f${NC}"
    echo -e "  停止服务: ${YELLOW}docker compose -f $COMPOSE_FILE down${NC}"
    echo -e "  重启服务: ${YELLOW}docker compose -f $COMPOSE_FILE restart${NC}"
    echo ""
    
    echo -e "${BLUE}配置文件位置:${NC}"
    echo -e "  环境配置: ${YELLOW}.env${NC}"
    echo -e "  应用配置: ${YELLOW}./config/${NC}"
    echo -e "  日志文件: ${YELLOW}./logs/${NC}"
    echo -e "  下载目录: ${YELLOW}./downloads/${NC}"
    echo -e "  缩略图目录: ${YELLOW}./thumbnails/${NC}"
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
