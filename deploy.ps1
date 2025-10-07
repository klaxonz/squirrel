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

# 检查 Docker 和 Docker Compose
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
    
    $envContent = @"
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
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    
    Write-ColorOutput Green "✓ .env 文件创建成功"
    Write-ColorOutput Yellow "提示: 请根据需要修改 .env 文件中的配置"
}

# 创建必要的目录
function Create-Directories {
    Write-ColorOutput Yellow "[3/5] 创建必要的目录..."
    
    $directories = @("config", "logs", "downloads", "postgres\data", "redis\data")
    
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
        if (Test-Path ".\build_plugins.ps1") {
            & .\build_plugins.ps1 -Dev
        }
        docker build -t klaxonz/squirrel:latest .
    } else {
        Write-ColorOutput Yellow "从 Docker Hub 拉取镜像..."
        docker compose pull
    }
    
    Write-ColorOutput Green "✓ 镜像准备完成"
}

# 启动服务
function Start-Services {
    Write-ColorOutput Yellow "[5/5] 启动服务..."
    
    docker compose up -d
    
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
    docker compose ps
    
    Write-Output ""
    Write-ColorOutput Blue "访问地址:"
    Write-ColorOutput Green "  http://localhost:8000"
    Write-Output ""
    
    Write-ColorOutput Blue "常用命令:"
    Write-ColorOutput Yellow "  查看日志: docker compose logs -f"
    Write-ColorOutput Yellow "  停止服务: docker compose down"
    Write-ColorOutput Yellow "  重启服务: docker compose restart"
    Write-Output ""
    
    Write-ColorOutput Blue "配置文件位置:"
    Write-ColorOutput Yellow "  环境配置: .env"
    Write-ColorOutput Yellow "  应用配置: .\config\"
    Write-ColorOutput Yellow "  日志文件: .\logs\"
    Write-ColorOutput Yellow "  下载目录: .\downloads\"
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

