#!/bin/bash

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
IMAGE_NAME="klaxonz/squirrel"
CF_BYPASS_IMAGE_NAME="klaxonz/squirrel-cf-bypass"
MUSIC_API_IMAGE_NAME="klaxonz/squirrel-music-api"
PLATFORM="linux/amd64,linux/arm64"

# 获取版本号
VERSION=$(grep "^__version__[[:space:]]*=" squirrel-backend/__init__.py | awk -F "['\"]" '{print $2}')
CF_BYPASS_VERSION=$(grep "^__version__[[:space:]]*=" squirrel-cf-bypass/src/squirrel_cf_bypass/__init__.py | awk -F "['\"]" '{print $2}')
MUSIC_API_VERSION=$(grep '"version"' squirrel-music-api/package.json | head -1 | awk -F '"' '{print $4}')

if [ -z "$VERSION" ]; then
    echo -e "${RED}错误: 无法从 squirrel-backend/__init__.py 获取版本号${NC}"
    exit 1
fi

if [ -z "$CF_BYPASS_VERSION" ]; then
    echo -e "${RED}错误: 无法从 squirrel-cf-bypass 获取版本号${NC}"
    exit 1
fi

if [ -z "$MUSIC_API_VERSION" ]; then
    echo -e "${RED}错误: 无法从 squirrel-music-api/package.json 获取版本号${NC}"
    exit 1
fi

# 显示使用说明
usage() {
    cat << EOF
使用方法: $0 [选项]

选项:
    -h, --help              显示此帮助信息
    -p, --push              推送镜像到仓库
    -m, --multi-platform    构建多平台镜像 (linux/amd64,linux/arm64)
    --no-cache              不使用缓存构建

示例:
    $0                      # 构建应用镜像
    $0 -p                   # 构建并推送应用镜像
    $0 -m                   # 构建多平台应用镜像
EOF
}

# 解析参数
PUSH=false
MULTI_PLATFORM=false
NO_CACHE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
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
        *)
            echo -e "${RED}未知选项: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

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

build_cf_bypass_image() {
    echo -e "${YELLOW}==> 构建 sidecar 镜像 $CF_BYPASS_IMAGE_NAME:$CF_BYPASS_VERSION...${NC}"

    if [ "$MULTI_PLATFORM" = true ]; then
        echo -e "${YELLOW}构建多平台 sidecar 镜像 ($PLATFORM)...${NC}"
        if [ "$PUSH" = true ]; then
            docker buildx build \
                --platform $PLATFORM \
                --push \
                $NO_CACHE \
                -t "$CF_BYPASS_IMAGE_NAME:$CF_BYPASS_VERSION" \
                -t "$CF_BYPASS_IMAGE_NAME:latest" \
                ./squirrel-cf-bypass
        else
            echo -e "${RED}错误: 多平台构建需要推送到仓库，请添加 -p 参数${NC}"
            exit 1
        fi
    else
        docker build $NO_CACHE -t "$CF_BYPASS_IMAGE_NAME:$CF_BYPASS_VERSION" ./squirrel-cf-bypass
        docker tag "$CF_BYPASS_IMAGE_NAME:$CF_BYPASS_VERSION" "$CF_BYPASS_IMAGE_NAME:latest"

        if [ "$PUSH" = true ]; then
            docker push "$CF_BYPASS_IMAGE_NAME:$CF_BYPASS_VERSION"
            docker push "$CF_BYPASS_IMAGE_NAME:latest"
        fi
    fi

    echo -e "${GREEN}✓ sidecar 镜像构建完成${NC}"
}

build_music_api_image() {
    echo -e "${YELLOW}==> 构建 music sidecar 镜像 $MUSIC_API_IMAGE_NAME:$MUSIC_API_VERSION...${NC}"

    if [ "$MULTI_PLATFORM" = true ]; then
        echo -e "${YELLOW}构建多平台 music sidecar 镜像 ($PLATFORM)...${NC}"
        if [ "$PUSH" = true ]; then
            docker buildx build \
                --platform $PLATFORM \
                --push \
                $NO_CACHE \
                -t "$MUSIC_API_IMAGE_NAME:$MUSIC_API_VERSION" \
                -t "$MUSIC_API_IMAGE_NAME:latest" \
                ./squirrel-music-api
        else
            echo -e "${RED}错误: 多平台构建需要推送到仓库，请添加 -p 参数${NC}"
            exit 1
        fi
    else
        docker build $NO_CACHE -t "$MUSIC_API_IMAGE_NAME:$MUSIC_API_VERSION" ./squirrel-music-api
        docker tag "$MUSIC_API_IMAGE_NAME:$MUSIC_API_VERSION" "$MUSIC_API_IMAGE_NAME:latest"

        if [ "$PUSH" = true ]; then
            docker push "$MUSIC_API_IMAGE_NAME:$MUSIC_API_VERSION"
            docker push "$MUSIC_API_IMAGE_NAME:latest"
        fi
    fi

    echo -e "${GREEN}✓ music sidecar 镜像构建完成${NC}"
}

# 主流程
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}   Squirrel Docker 镜像构建工具${NC}"
echo -e "${GREEN}=====================================${NC}"
echo -e "版本号: ${YELLOW}$VERSION${NC}"
echo ""

# 构建应用镜像
build_app_image

# 构建 Cloudflare bypass sidecar 镜像
build_cf_bypass_image

# 构建 KuGou music sidecar 镜像
build_music_api_image

# 总结
echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}构建完成！${NC}"
echo -e "${GREEN}=====================================${NC}"
echo -e "镜像标签:"
echo -e "  - ${YELLOW}$IMAGE_NAME:$VERSION${NC}"
echo -e "  - ${YELLOW}$IMAGE_NAME:latest${NC}"
echo -e "  - ${YELLOW}$CF_BYPASS_IMAGE_NAME:$CF_BYPASS_VERSION${NC}"
echo -e "  - ${YELLOW}$CF_BYPASS_IMAGE_NAME:latest${NC}"
echo -e "  - ${YELLOW}$MUSIC_API_IMAGE_NAME:$MUSIC_API_VERSION${NC}"
echo -e "  - ${YELLOW}$MUSIC_API_IMAGE_NAME:latest${NC}"

if [ "$PUSH" = true ]; then
    echo -e "\n${GREEN}✓ 镜像已推送到仓库${NC}"
fi

echo ""
echo -e "运行容器:"
echo -e "  ${YELLOW}docker compose up -d${NC}"
