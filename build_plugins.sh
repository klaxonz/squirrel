#!/bin/bash

# Squirrel 插件一键打包脚本
# 用于构建 squirrel-plugins 目录下的所有插件并打包成 zip 文件
#
# 注意：Windows 用户请使用 build_plugins.ps1 (PowerShell 版本)
# 或在 Git Bash / WSL 中运行此脚本

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGINS_DIR="$SCRIPT_DIR/squirrel-plugins"
DIST_DIR="$SCRIPT_DIR/plugin_packages"
PLUGINS_EXT_DIR="$SCRIPT_DIR/squirrel-backend/plugins_ext"

# 开发模式标志
DEV_MODE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dev)
            DEV_MODE=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo "选项:"
            echo "  -d, --dev    开发模式，自动解压插件到 squirrel-backend/plugins_ext 目录"
            echo "  -h, --help   显示此帮助信息"
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            echo "使用 -h 或 --help 查看帮助"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}=== Squirrel 插件一键打包工具 ===${NC}"
echo "插件目录: $PLUGINS_DIR"
echo "输出目录: $DIST_DIR"
if [ "$DEV_MODE" = true ]; then
    echo -e "${YELLOW}开发模式: 已启用 (将自动部署到 plugins_ext)${NC}"
    echo "部署目录: $PLUGINS_EXT_DIR"
fi
echo

# 检查插件目录是否存在
if [ ! -d "$PLUGINS_DIR" ]; then
    echo -e "${RED}错误: 插件目录不存在: $PLUGINS_DIR${NC}"
    exit 1
fi

# 创建输出目录
mkdir -p "$DIST_DIR"

# 清理之前的构建文件
echo -e "${YELLOW}清理之前的构建文件...${NC}"
rm -rf "$DIST_DIR"/*

# 如果是开发模式，清理 plugins_ext 目录
if [ "$DEV_MODE" = true ]; then
    if [ -d "$PLUGINS_EXT_DIR" ]; then
        echo -e "${YELLOW}清理 plugins_ext 目录...${NC}"
        rm -rf "$PLUGINS_EXT_DIR"/*
    else
        mkdir -p "$PLUGINS_EXT_DIR"
    fi
fi

# 获取所有插件目录
PLUGINS=($(find "$PLUGINS_DIR" -maxdepth 1 -type d -not -path "$PLUGINS_DIR" -exec basename {} \; | grep -v "^\."))

if [ ${#PLUGINS[@]} -eq 0 ]; then
    echo -e "${RED}错误: 没有找到任何插件目录${NC}"
    exit 1
fi

echo -e "${GREEN}找到 ${#PLUGINS[@]} 个插件: ${PLUGINS[*]}${NC}"
echo

# 构建每个插件
SUCCESS_COUNT=0
FAILED_PLUGINS=()

for plugin in "${PLUGINS[@]}"; do
    plugin_path="$PLUGINS_DIR/$plugin"
    
    # 跳过非目录文件（如 README.md）
    if [ ! -d "$plugin_path" ]; then
        continue
    fi
    
    echo -e "${BLUE}正在打包插件: $plugin${NC}"

    # 检查 src 目录是否存在
    if [ ! -d "$plugin_path/src" ]; then
        echo -e "${RED}✗ $plugin 打包失败: 未找到 src 目录${NC}"
        FAILED_PLUGINS+=("$plugin")
        echo
        continue
    fi

    plugin_package_dir="$DIST_DIR/$plugin"
    mkdir -p "$plugin_package_dir"

    # 复制插件源文件
    cp -R "$plugin_path/" "$plugin_package_dir/" 2>/dev/null || true
    find "$plugin_package_dir" -name "__pycache__" -type d -prune -exec rm -rf {} +

    # 创建 zip 包
    cd "$DIST_DIR"
    zip_file="${plugin}_plugin.zip"
    zip -r "$zip_file" "$plugin" > /dev/null

    # 如果是开发模式，解压到 plugins_ext 目录
    if [ "$DEV_MODE" = true ]; then
        echo -e "${BLUE}  → 部署到 plugins_ext/$plugin${NC}"
        plugin_deploy_dir="$PLUGINS_EXT_DIR/$plugin"
        mkdir -p "$plugin_deploy_dir"
        unzip -q "$zip_file" -d "$PLUGINS_EXT_DIR"
        echo -e "${GREEN}  ✓ 已部署到开发环境${NC}"
    fi

    # 删除临时目录
    rm -rf "$plugin"

    echo -e "${GREEN}✓ $plugin 打包完成: $zip_file${NC}"
    ((SUCCESS_COUNT++))
    echo
done

# 返回原目录
cd "$SCRIPT_DIR"

# 输出构建结果
echo -e "${BLUE}=== 构建完成 ===${NC}"
echo -e "${GREEN}成功构建插件数量: $SUCCESS_COUNT${NC}"

if [ ${#FAILED_PLUGINS[@]} -gt 0 ]; then
    echo -e "${RED}失败的插件: ${FAILED_PLUGINS[*]}${NC}"
fi

echo
echo -e "${GREEN}所有插件包已保存到: $DIST_DIR${NC}"
echo

# 列出生成的文件
if [ -d "$DIST_DIR" ] && [ "$(ls -A "$DIST_DIR")" ]; then
    echo -e "${BLUE}生成的插件包:${NC}"
    ls -la "$DIST_DIR"/*.zip 2>/dev/null || echo "没有生成 zip 文件"
else
    echo -e "${YELLOW}警告: 没有生成任何插件包${NC}"
fi

# 如果是开发模式，显示部署信息
if [ "$DEV_MODE" = true ] && [ -d "$PLUGINS_EXT_DIR" ] && [ "$(ls -A "$PLUGINS_EXT_DIR")" ]; then
    echo
    echo -e "${BLUE}已部署的插件:${NC}"
    ls -la "$PLUGINS_EXT_DIR"
    echo
    echo -e "${GREEN}✓ 开发模式部署完成！插件已自动安装到 plugins_ext 目录${NC}"
fi

echo -e "${GREEN}完成!${NC}"
