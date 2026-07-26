param(
  [Parameter(Mandatory = $true)][int]$RelX,
  [Parameter(Mandatory = $true)][int]$RelY,
  [int]$WaitMs = 900
)

$ErrorActionPreference = 'Stop'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinClick {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool PhysicalToLogicalPointForPerMonitorDPI(IntPtr hWnd, ref POINT lpPoint);
  [DllImport("user32.dll")] public static extern bool LogicalToPhysicalPointForPerMonitorDPI(IntPtr hWnd, ref POINT lpPoint);
  [DllImport("shcore.dll")] public static extern int SetProcessDpiAwareness(int value);
  public const uint LEFTDOWN = 0x0002;
  public const uint LEFTUP = 0x0004;
  public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
  public struct POINT { public int X; public int Y; }
}
'@

# PROCESS_PER_MONITOR_DPI_AWARE = 2
try { [void][WinClick]::SetProcessDpiAwareness(2) } catch {}

$p = Get-Process electron |
  Where-Object {
    $_.MainWindowHandle -ne [IntPtr]::Zero -and
    ($_.MainWindowTitle -match 'Squirrel|归仓|推荐|视频|历史|订阅|设置|音乐' -or $_.Id -eq 56572)
  } |
  Select-Object -First 1
if (-not $p) { throw 'No Squirrel window' }

$hwnd = $p.MainWindowHandle
if ([WinClick]::IsIconic($hwnd)) { [void][WinClick]::ShowWindow($hwnd, 9) }
[void][WinClick]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 200

$r = New-Object WinClick+RECT
[void][WinClick]::GetWindowRect($hwnd, [ref]$r)
# RelX/RelY are physical pixels relative to window top-left (same space as PrintWindow capture)
$x = $r.Left + $RelX
$y = $r.Top + $RelY
[void][WinClick]::SetCursorPos($x, $y)
Start-Sleep -Milliseconds 50
[WinClick]::mouse_event([WinClick]::LEFTDOWN, 0, 0, 0, [UIntPtr]::Zero)
[WinClick]::mouse_event([WinClick]::LEFTUP, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds $WaitMs
Write-Output ("clicked rel={0},{1} abs={2},{3} win=({4},{5})-({6},{7}) title={8}" -f `
  $RelX, $RelY, $x, $y, $r.Left, $r.Top, $r.Right, $r.Bottom, $p.MainWindowTitle)
