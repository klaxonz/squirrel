$ErrorActionPreference = 'Stop'

$p = Get-Process electron |
  Where-Object {
    $_.MainWindowHandle -ne [IntPtr]::Zero -and
    ($_.MainWindowTitle -match 'Squirrel|归仓|推荐|视频|历史|订阅|设置' -or $_.Id -eq 56572)
  } |
  Select-Object -First 1
if (-not $p) {
  $p = Get-Process electron | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } | Select-Object -First 1
}
if (-not $p) { throw 'No electron window found' }

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinFocus {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
  [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr hwnd, uint dwFlags);
  public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
'@

Add-Type -AssemblyName System.Windows.Forms

Write-Output '=== Screens ==='
$i = 0
foreach ($s in [System.Windows.Forms.Screen]::AllScreens) {
  Write-Output ("[{0}] Primary={1} Bounds={2},{3} {4}x{5} Working={6},{7} {8}x{9}" -f `
    $i, $s.Primary, $s.Bounds.X, $s.Bounds.Y, $s.Bounds.Width, $s.Bounds.Height, `
    $s.WorkingArea.X, $s.WorkingArea.Y, $s.WorkingArea.Width, $s.WorkingArea.Height)
  $i++
}

$hwnd = $p.MainWindowHandle
$cur = New-Object WinFocus+RECT
[void][WinFocus]::GetWindowRect($hwnd, [ref]$cur)
Write-Output ("Before: pid={0} title={1} L={2} T={3} R={4} B={5}" -f $p.Id, $p.MainWindowTitle, $cur.Left, $cur.Top, $cur.Right, $cur.Bottom)

# Prefer primary working area so taskbar stays; computer capture often composites both monitors
$target = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
if ([WinFocus]::IsIconic($hwnd)) { [void][WinFocus]::ShowWindow($hwnd, 9) }
[void][WinFocus]::ShowWindow($hwnd, 1) # normal first so MoveWindow sticks
[void][WinFocus]::MoveWindow($hwnd, $target.X, $target.Y, $target.Width, $target.Height, $true)
[void][WinFocus]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 500

$after = New-Object WinFocus+RECT
[void][WinFocus]::GetWindowRect($hwnd, [ref]$after)
Write-Output ("After:  L={0} T={1} R={2} B={3} W={4} H={5} primaryWork={6}x{7}@{8},{9}" -f `
  $after.Left, $after.Top, $after.Right, $after.Bottom, `
  ($after.Right - $after.Left), ($after.Bottom - $after.Top), `
  $target.Width, $target.Height, $target.X, $target.Y)
