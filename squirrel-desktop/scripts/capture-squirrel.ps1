param(
  [string]$OutName = ''
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinCap {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdcBlt, uint nFlags);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
  [DllImport("shcore.dll")] public static extern int SetProcessDpiAwareness(int value);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
'@

try { [void][WinCap]::SetProcessDpiAwareness(2) } catch {
  try { [void][WinCap]::SetProcessDPIAware() } catch {}
}

$p = Get-Process electron |
  Where-Object {
    $_.MainWindowHandle -ne [IntPtr]::Zero -and
    ($_.MainWindowTitle -match 'Squirrel|归仓|推荐|视频|历史|订阅|设置|音乐' -or $_.Id -eq 56572)
  } |
  Select-Object -First 1
if (-not $p) {
  $p = Get-Process electron | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } | Select-Object -First 1
}
if (-not $p) { throw 'No electron window found' }

$hwnd = $p.MainWindowHandle
if ([WinCap]::IsIconic($hwnd)) { [void][WinCap]::ShowWindow($hwnd, 9) }
[void][WinCap]::ShowWindow($hwnd, 5)
[void][WinCap]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 400

$r = New-Object WinCap+RECT
[void][WinCap]::GetWindowRect($hwnd, [ref]$r)
$w = [Math]::Max(1, $r.Right - $r.Left)
$h = [Math]::Max(1, $r.Bottom - $r.Top)

$outDir = Join-Path $PSScriptRoot '..\..\e2e-shots'
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
if (-not $OutName) { $OutName = "squirrel-full-{0}.png" -f $stamp }
$out = Join-Path $outDir $OutName

# Prefer screen crop at physical coordinates (full window, dual-monitor safe for target rect)
$bmp = New-Object System.Drawing.Bitmap $w, $h, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left, $r.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$g.Dispose()

# If blank, try PrintWindow as fallback
$c = $bmp.GetPixel([int]($w / 2), [int]($h / 2))
$sample = [int]$c.R + [int]$c.G + [int]$c.B
$method = 'CopyFromScreen'
if ($sample -lt 12) {
  $bmp.Dispose()
  $bmp = New-Object System.Drawing.Bitmap $w, $h, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.Clear([System.Drawing.Color]::Magenta)
  $hdc = $g.GetHdc()
  [void][WinCap]::PrintWindow($hwnd, $hdc, 2)
  $g.ReleaseHdc($hdc)
  $g.Dispose()
  $method = 'PrintWindow'
}

$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output $out
Write-Output ("pid={0} title={1} capture={2}x{3} at {4},{5} method={6}" -f `
  $p.Id, $p.MainWindowTitle, $w, $h, $r.Left, $r.Top, $method)
