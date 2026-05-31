# Squirrel 快速部署脚本 (PowerShell)

$ErrorActionPreference = "Stop"

# 颜色函数
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

# 显示欢迎信息
Write-ColorOutput Green @"
 ____              _                _ 
/ ___|  __ _ _   _(_)_ __ _ __ ___| |
\___ \ / _`` | | | | | '__| '__/ _ \ |
 ___) | (_| | |_| | | |  | | |  __/ |
|____/ \__, |\__,_|_|_|  |_|  \___|_|
          |_|                        
"@

Write-ColorOutput Blue "Squirrel 快速部署脚本"
Write-ColorOutput Blue "========================"
Write-Output ""

$script:COMPOSE_FILE = "docker-compose.yaml"

function Check-Requirements {
    Write-ColorOutput Yellow "[1/5] 检查环境依赖..."
    
    try {
        docker --version | Out-Null
    } catch {
        Write-ColorOutput Red "错误: 未找到 Docker，请先安装 Docker"
        exit 1
    }
    
    try {
        docker compose version | Out-Null
    } catch {
        try {
            docker-compose --version | Out-Null
        } catch {
            Write-ColorOutput Red "错误: 未找到 Docker Compose，请先安装 Docker Compose"
            exit 1
        }
    }
    
    Write-ColorOutput Green "✓ Docker 和 Docker Compose 已安装"
}

# 创建环境配置文件
function Create-EnvFile {
    Write-ColorOutput Yellow "[2/5] 创建环境配置文件..."
    
    if (Test-Path ".env") {
        Write-ColorOutput Yellow "⚠ .env 文件已存在，跳过创建"
        return
    }
    
    # 复制示例文件
    if (Test-Path "env.example") {
        Copy-Item "env.example" ".env"
        Write-ColorOutput Green "✓ .env 文件创建成功（已从 env.example 复制）"
        
        Write-ColorOutput Yellow "提示：部署前请检查 .env 中的密码、缩略图路径和 Cloudflare 服务地址"
    } else {
        Write-ColorOutput Red "错误: 未找到 env.example 文件"
        exit 1
    }
}

# 创建必要的目录
function Create-Directories {
    Write-ColorOutput Yellow "[3/5] 创建必要的目录..."
    $directories = @("config", "logs", "downloads", "thumbnails", "postgres\data", "redis\data")
    
    foreach ($dir in $directories) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-ColorOutput Green "✓ 目录创建成功"
}

# 构建或拉取镜像
function Setup-Images {
    Write-ColorOutput Yellow "[4/5] 准备 Docker 镜像..."
    
    $build = Read-Host "是否从源码构建镜像？(y/N)"
    
    if ($build -eq "y" -or $build -eq "Y") {
        Write-ColorOutput Yellow "开始构建镜像..."
        docker build --target runtime-base -t ghcr.io/klaxonz/squirrel-base:runtime -f Dockerfile.base .
        docker build --target build-base -t ghcr.io/klaxonz/squirrel-base:build -f Dockerfile.base .
        docker build -t klaxonz/squirrel:latest .
        docker build -t klaxonz/squirrel-cf-bypass:latest .\squirrel-cf-bypass
        docker build -t klaxonz/squirrel-music-api:latest .\squirrel-music-api
    } else {
        Write-ColorOutput Yellow "从 Docker Hub 拉取镜像..."
        docker compose -f $script:COMPOSE_FILE pull
    }
    
    Write-ColorOutput Green "✓ 镜像准备完成"
}

# 启动服务
function Start-Services {
    Write-ColorOutput Yellow "[5/5] 启动服务..."
    
    docker compose -f $script:COMPOSE_FILE up -d
    
    Write-ColorOutput Green "✓ 服务启动成功"
}

# 显示部署结果
function Show-Result {
    Write-Output ""
    Write-ColorOutput Green "====================================="
    Write-ColorOutput Green "部署完成！"
    Write-ColorOutput Green "====================================="
    Write-Output ""
    
    # 等待几秒让服务启动
    Write-ColorOutput Yellow "等待服务启动..."
    Start-Sleep -Seconds 5
    
    # 显示服务状态
    Write-ColorOutput Blue "服务状态:"
    docker compose -f $script:COMPOSE_FILE ps
    
    Write-Output ""
    Write-ColorOutput Blue "访问地址:"
    Write-ColorOutput Green "  http://localhost:8001"
    Write-Output ""
    
    Write-ColorOutput Blue "常用命令:"
    Write-ColorOutput Yellow "  查看日志: docker compose -f $($script:COMPOSE_FILE) logs -f"
    Write-ColorOutput Yellow "  停止服务: docker compose -f $($script:COMPOSE_FILE) down"
    Write-ColorOutput Yellow "  重启服务: docker compose -f $($script:COMPOSE_FILE) restart"
    Write-Output ""
    
    Write-ColorOutput Blue "配置文件位置:"
    Write-ColorOutput Yellow "  环境配置: .env"
    Write-ColorOutput Yellow "  应用配置: .\config\"
    Write-ColorOutput Yellow "  日志文件: .\logs\"
    Write-ColorOutput Yellow "  下载目录: .\downloads\"
    Write-ColorOutput Yellow "  缩略图目录: .\thumbnails\"
    Write-Output ""
    
    Write-ColorOutput Yellow "提示: 首次启动可能需要等待数据库初始化，请稍候"
}

# 主流程
function Main {
    try {
        Check-Requirements
        Create-EnvFile
        Create-Directories
        Setup-Images
        Start-Services
        Show-Result
    } catch {
        Write-ColorOutput Red "部署失败: $_"
        exit 1
    }
}

# 执行主流程
Main


