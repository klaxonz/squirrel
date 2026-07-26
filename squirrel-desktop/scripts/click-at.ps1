param(
  [Parameter(Mandatory = $true)][int]$X,
  [Parameter(Mandatory = $true)][int]$Y,
  [int]$WaitMs = 700
)

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class MouseClick {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
  public const uint LEFTDOWN = 0x0002;
  public const uint LEFTUP = 0x0004;
}
'@

[void][MouseClick]::SetCursorPos($X, $Y)
Start-Sleep -Milliseconds 60
[MouseClick]::mouse_event([MouseClick]::LEFTDOWN, 0, 0, 0, [UIntPtr]::Zero)
[MouseClick]::mouse_event([MouseClick]::LEFTUP, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds $WaitMs
Write-Output ("clicked {0},{1}" -f $X, $Y)
