# Squirrel Plugin Builder (PowerShell Version)
# Build and package all plugins in squirrel-plugins directory

param(
    [switch]$Dev,
    [switch]$Help
)

# Show help
if ($Help) {
    Write-Host "Usage: .\build_plugins.ps1 [options]"
    Write-Host "Options:"
    Write-Host "  -Dev     Dev mode, auto deploy to squirrel-backend/plugins_ext"
    Write-Host "  -Help    Show this help"
    exit 0
}

# Directories
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginsDir = Join-Path $ScriptDir "squirrel-plugins"
$DistDir = Join-Path $ScriptDir "plugin_packages"
$PluginsExtDir = Join-Path $ScriptDir "squirrel-backend\plugins_ext"

# Dev mode flag
$DevMode = $Dev.IsPresent

# Show header
Write-Host "=== Squirrel Plugin Builder ===" -ForegroundColor Blue
Write-Host "Plugins dir: $PluginsDir"
Write-Host "Output dir: $DistDir"
if ($DevMode) {
    Write-Host "Dev mode: Enabled (will deploy to plugins_ext)" -ForegroundColor Yellow
    Write-Host "Deploy dir: $PluginsExtDir"
}
Write-Host ""

# Check plugins directory
if (-not (Test-Path $PluginsDir)) {
    Write-Host "Error: Plugins directory not found: $PluginsDir" -ForegroundColor Red
    exit 1
}

# Create output directory
if (-not (Test-Path $DistDir)) {
    New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
}

# Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
Get-ChildItem -Path $DistDir -Include *.* -File -Recurse | ForEach-Object { Remove-Item $_.FullName -Force }
Get-ChildItem -Path $DistDir -Directory | ForEach-Object { Remove-Item $_.FullName -Recurse -Force }

# Clean plugins_ext if dev mode
if ($DevMode) {
    if (Test-Path $PluginsExtDir) {
        Write-Host "Cleaning plugins_ext..." -ForegroundColor Yellow
        Get-ChildItem -Path $PluginsExtDir -Include *.* -File -Recurse | ForEach-Object { Remove-Item $_.FullName -Force }
        Get-ChildItem -Path $PluginsExtDir -Directory | ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
    } else {
        New-Item -ItemType Directory -Path $PluginsExtDir -Force | Out-Null
    }
}

# Get all plugin directories
$Plugins = Get-ChildItem -Path $PluginsDir -Directory | Where-Object { $_.Name -notmatch '^\.' }

if ($Plugins.Count -eq 0) {
    Write-Host "Error: No plugin directories found" -ForegroundColor Red
    exit 1
}

$PluginNames = $Plugins | ForEach-Object { $_.Name }
Write-Host "Found $($Plugins.Count) plugins: $($PluginNames -join ', ')" -ForegroundColor Green
Write-Host ""

# Build each plugin
$SuccessCount = 0
$FailedPlugins = @()

foreach ($plugin in $Plugins) {
    $pluginName = $plugin.Name
    $pluginPath = $plugin.FullName
    
    Write-Host "Packaging plugin: $pluginName" -ForegroundColor Blue

    # Check src directory
    $srcPath = Join-Path $pluginPath "src"
    if (-not (Test-Path $srcPath)) {
        Write-Host "[X] $pluginName failed: src directory not found" -ForegroundColor Red
        $FailedPlugins += $pluginName
        Write-Host ""
        continue
    }

    $pluginPackageDir = Join-Path $DistDir $pluginName
    
    # Copy plugin source
    Copy-Item -Path $pluginPath -Destination $pluginPackageDir -Recurse -Force
    
    # Remove __pycache__
    Get-ChildItem -Path $pluginPackageDir -Directory -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force

    # Create zip package
    $zipFile = Join-Path $DistDir "${pluginName}_plugin.zip"
    
    # Use Compress-Archive (PowerShell 5.0+)
    if ($PSVersionTable.PSVersion.Major -ge 5) {
        Compress-Archive -Path $pluginPackageDir -DestinationPath $zipFile -Force
    } else {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory($pluginPackageDir, $zipFile)
    }

    # Deploy to plugins_ext if dev mode
    if ($DevMode) {
        Write-Host "  -> Deploying to plugins_ext/$pluginName" -ForegroundColor Blue
        $pluginDeployDir = Join-Path $PluginsExtDir $pluginName
        
        if ($PSVersionTable.PSVersion.Major -ge 5) {
            Expand-Archive -Path $zipFile -DestinationPath $PluginsExtDir -Force
        } else {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            [System.IO.Compression.ZipFile]::ExtractToDirectory($zipFile, $PluginsExtDir)
        }
        
        Write-Host "  [OK] Deployed to dev environment" -ForegroundColor Green
    }

    # Remove temp directory
    Remove-Item -Path $pluginPackageDir -Recurse -Force

    Write-Host "[OK] $pluginName packaged: ${pluginName}_plugin.zip" -ForegroundColor Green
    $SuccessCount++
    Write-Host ""
}

# Show build results
Write-Host "=== Build Complete ===" -ForegroundColor Blue
Write-Host "Successfully built: $SuccessCount plugins" -ForegroundColor Green

if ($FailedPlugins.Count -gt 0) {
    Write-Host "Failed plugins: $($FailedPlugins -join ', ')" -ForegroundColor Red
}

Write-Host ""
Write-Host "All plugin packages saved to: $DistDir" -ForegroundColor Green
Write-Host ""

# List generated files
$zipFiles = Get-ChildItem -Path $DistDir -Filter "*.zip" -ErrorAction SilentlyContinue
if ($zipFiles) {
    Write-Host "Generated packages:" -ForegroundColor Blue
    $zipFiles | ForEach-Object {
        $size = "{0:N2} KB" -f ($_.Length / 1KB)
        Write-Host "  $($_.Name) - $size"
    }
} else {
    Write-Host "Warning: No packages generated" -ForegroundColor Yellow
}

# Show deployment info if dev mode
if ($DevMode -and (Test-Path $PluginsExtDir)) {
    $deployedPlugins = Get-ChildItem -Path $PluginsExtDir -Directory -ErrorAction SilentlyContinue
    if ($deployedPlugins) {
        Write-Host ""
        Write-Host "Deployed plugins:" -ForegroundColor Blue
        $deployedPlugins | ForEach-Object {
            Write-Host "  $($_.Name)"
        }
        Write-Host ""
        Write-Host "[OK] Dev mode deployment complete!" -ForegroundColor Green
    }
}

Write-Host "Done!" -ForegroundColor Green
