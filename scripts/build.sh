#!/bin/bash

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
IMAGE_NAME="klaxonz/squirrel"
BASE_IMAGE_NAME="ghcr.io/klaxonz/squirrel-base"
PLATFORM="linux/amd64,linux/arm64"

# 获取版本号
VERSION=$(grep '__version__' squirrel-backend/__init__.py | awk -F "'" '{print $2}')

if [ -z "$VERSION" ]; then
    echo -e "${RED}错误: 无法从 squirrel-backend/__init__.py 获取版本号${NC}"
    exit 1
fi

# 显示使用说明
usage() {
    cat << EOF
使用方法: $0 [选项]

选项:
    -h, --help              显示此帮助信息
    -b, --build-base        构建基础镜像
    -p, --push              推送镜像到仓库
    -m, --multi-platform    构建多平台镜像 (linux/amd64,linux/arm64)
    --no-cache              不使用缓存构建
    --skip-plugins          跳过插件构建

示例:
    $0                      # 仅构建应用镜像
    $0 -b                   # 构建基础镜像
    $0 -p                   # 构建并推送应用镜像
    $0 -b -p                # 构建并推送基础镜像和应用镜像
    $0 -m                   # 构建多平台应用镜像
EOF
}

# 解析参数
BUILD_BASE=false
PUSH=false
MULTI_PLATFORM=false
NO_CACHE=""
SKIP_PLUGINS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -b|--build-base)
            BUILD_BASE=true
            shift
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -m|--multi-platform)
            MULTI_PLATFORM=true
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --skip-plugins)
            SKIP_PLUGINS=true
            shift
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# 构建插件
build_plugins() {
    if [ "$SKIP_PLUGINS" = false ]; then
        echo -e "${YELLOW}==> 构建插件...${NC}"
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [ -f "$SCRIPT_DIR/build_plugins.sh" ]; then
            "$SCRIPT_DIR/build_plugins.sh" -d
            echo -e "${GREEN}✓ 插件构建完成${NC}"
        else
            echo -e "${YELLOW}⚠ 未找到 build_plugins.sh，跳过插件构建${NC}"
        fi
    else
        echo -e "${YELLOW}==> 跳过插件构建${NC}"
    fi
}

# 构建基础镜像
build_base_image() {
    echo -e "${YELLOW}==> 构建基础镜像 $BASE_IMAGE_NAME:latest...${NC}"
    
    if [ "$MULTI_PLATFORM" = true ]; then
        echo -e "${YELLOW}构建多平台基础镜像 ($PLATFORM)...${NC}"
        if [ "$PUSH" = true ]; then
            docker buildx build \
                --platform $PLATFORM \
                --push \
                $NO_CACHE \
                -t "$BASE_IMAGE_NAME:latest" \
                -f Dockerfile.base .
        else
            echo -e "${RED}错误: 多平台构建需要推送到仓库，请添加 -p 参数${NC}"
            exit 1
        fi
    else
        docker build $NO_CACHE -t "$BASE_IMAGE_NAME:latest" -f Dockerfile.base .
        if [ "$PUSH" = true ]; then
            docker push "$BASE_IMAGE_NAME:latest"
        fi
    fi
    
    echo -e "${GREEN}✓ 基础镜像构建完成${NC}"
}

# 构建应用镜像
build_app_image() {
    echo -e "${YELLOW}==> 构建应用镜像 $IMAGE_NAME:$VERSION...${NC}"
    
    if [ "$MULTI_PLATFORM" = true ]; then
        echo -e "${YELLOW}构建多平台应用镜像 ($PLATFORM)...${NC}"
        if [ "$PUSH" = true ]; then
            docker buildx build \
                --platform $PLATFORM \
                --push \
                $NO_CACHE \
                -t "$IMAGE_NAME:$VERSION" \
                -t "$IMAGE_NAME:latest" .
        else
            echo -e "${RED}错误: 多平台构建需要推送到仓库，请添加 -p 参数${NC}"
            exit 1
        fi
    else
        docker build $NO_CACHE -t "$IMAGE_NAME:$VERSION" .
        docker tag "$IMAGE_NAME:$VERSION" "$IMAGE_NAME:latest"
        
        if [ "$PUSH" = true ]; then
            docker push "$IMAGE_NAME:$VERSION"
            docker push "$IMAGE_NAME:latest"
        fi
    fi
    
    echo -e "${GREEN}✓ 应用镜像构建完成${NC}"
}

# 主流程
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}   Squirrel Docker 镜像构建工具${NC}"
echo -e "${GREEN}=====================================${NC}"
echo -e "版本号: ${YELLOW}$VERSION${NC}"
echo ""

# 构建插件
build_plugins

# 构建基础镜像
if [ "$BUILD_BASE" = true ]; then
    build_base_image
fi

# 构建应用镜像
build_app_image

# 总结
echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}构建完成！${NC}"
echo -e "${GREEN}=====================================${NC}"
echo -e "镜像标签:"
if [ "$BUILD_BASE" = true ]; then
    echo -e "  - ${YELLOW}$BASE_IMAGE_NAME:latest${NC}"
fi
echo -e "  - ${YELLOW}$IMAGE_NAME:$VERSION${NC}"
echo -e "  - ${YELLOW}$IMAGE_NAME:latest${NC}"

if [ "$PUSH" = true ]; then
    echo -e "\n${GREEN}✓ 镜像已推送到仓库${NC}"
fi

echo ""
echo -e "运行容器:"
echo -e "  ${YELLOW}docker compose up -d${NC}"

