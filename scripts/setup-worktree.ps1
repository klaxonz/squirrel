#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Create a new git worktree and share node_modules with the main worktree.

.DESCRIPTION
  This script creates a new git worktree for the given branch and links its
  node_modules to the main repo's node_modules via directory junctions
  (Windows) or symlinks (Linux/macOS). This avoids reinstalling all
  dependencies across multiple worktrees.

.PARAMETER Branch
  The branch name to check out in the new worktree (default: current branch).

.PARAMETER Path
  The filesystem path for the new worktree. Defaults to ../<repo-name>-<branch>.

.EXAMPLE
  .\scripts\setup-worktree.ps1 -Branch feature/new-ui
  .\scripts\setup-worktree.ps1 -Branch fix/bug -Path D:\Code\squirrel-hotfix
#>

param(
  [Parameter(Mandatory = $false)]
  [string]$Branch,

  [Parameter(Mandatory = $false)]
  [string]$Path
)

$ErrorActionPreference = "Stop"

# Resolve the main repository root
$MainRepo = git rev-parse --show-toplevel
if (-not $MainRepo) {
  Write-Error "Failed to detect main repository root. Are you inside a git repository?"
  exit 1
}

# Default branch = current branch
if (-not $Branch) {
  $Branch = git rev-parse --abbrev-ref HEAD
  Write-Host "Using current branch: $Branch"
}

# Default path = ../<repo-name>-<branch>
if (-not $Path) {
  $RepoName = Split-Path -Leaf $MainRepo
  $SafeBranch = $Branch -replace '[\\/:*?"<>|]', '-'
  $Path = Join-Path (Split-Path -Parent $MainRepo) "$RepoName-$SafeBranch"
  Write-Host "Using default path: $Path"
}

Write-Host ""

# Create the worktree
Write-Host "[1/3] Creating git worktree..." -ForegroundColor Cyan
git worktree add $Path $Branch
if ($LASTEXITCODE -ne 0) {
  Write-Error "Failed to create worktree"
  exit 1
}

Write-Host "[2/3] Setting up node_modules links..." -ForegroundColor Cyan

# List of workspace subprojects (relative to repo root)
$Workspaces = @(
  "squirrel-frontend",
  "squirrel-desktop",
  "squirrel-music-api",
  "squirrel-site-runtimes/youtube/src/squirrel_youtube/node"
)

$Linked = 0
$Skipped = 0

foreach ($ws in $Workspaces) {
  $srcModule = Join-Path $MainRepo "$ws\node_modules"
  $dstModule = Join-Path $Path "$ws\node_modules"

  # Remove existing node_modules if present (they might be empty dirs from checkout)
  if (Test-Path $dstModule) {
    Remove-Item -Recurse -Force $dstModule -ErrorAction SilentlyContinue
  }

  if (Test-Path $srcModule) {
    New-Item -ItemType Junction -Path $dstModule -Target $srcModule -Force | Out-Null
    Write-Host "  linked: $ws" -ForegroundColor Green
    $Linked++
  }
  else {
    Write-Host "  skipped (no node_modules): $ws" -ForegroundColor Yellow
    $Skipped++
  }
}

# Also link root node_modules
$srcRootModule = Join-Path $MainRepo "node_modules"
$dstRootModule = Join-Path $Path "node_modules"
if (Test-Path $dstRootModule) {
  Remove-Item -Recurse -Force $dstRootModule -ErrorAction SilentlyContinue
}
if (Test-Path $srcRootModule) {
  New-Item -ItemType Junction -Path $dstRootModule -Target $srcRootModule -Force | Out-Null
  Write-Host "  linked: (root)" -ForegroundColor Green
  $Linked++
}

Write-Host ""
Write-Host "[3/3] Done!" -ForegroundColor Cyan
Write-Host "  Linked: $Linked workspace(s)"
Write-Host "  Skipped: $Skipped (already had node_modules or none found)"
Write-Host "  Worktree: $Path"
Write-Host ""
Write-Host "You can now cd to the worktree and run any npm script:"
Write-Host "  cd $Path"
Write-Host "  npm -w squirrel-front run dev"
Write-Host "  npm -w squirrel-desktop run dev"
