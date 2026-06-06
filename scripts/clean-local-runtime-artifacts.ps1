param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$targets = @(
    (Join-Path $repoRoot 'squirrel-backend\radar.db')
)

$runtimeRoot = Join-Path $repoRoot 'squirrel-site-runtimes'
if (Test-Path -LiteralPath $runtimeRoot) {
    Get-ChildItem -LiteralPath $runtimeRoot -Directory | ForEach-Object {
        $targets += Join-Path $_.FullName 'runtime-logs'
        $targets += Join-Path $_.FullName 'runtime-audit'
    }
}

foreach ($target in $targets) {
    if (-not (Test-Path -LiteralPath $target)) {
        continue
    }

    $resolvedTarget = (Resolve-Path -LiteralPath $target).Path
    if (-not $resolvedTarget.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside repository: $resolvedTarget"
    }

    if ($DryRun) {
        Write-Output "Would remove: $resolvedTarget"
        continue
    }

    Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
    Write-Output "Removed: $resolvedTarget"
}
