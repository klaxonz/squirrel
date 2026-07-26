$ErrorActionPreference = 'Stop'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class KeySend {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
  public const uint KEYEVENTF_KEYUP = 0x0002;
  public const byte VK_CONTROL = 0x11;
  public const byte VK_R = 0x52;
  public const byte VK_F5 = 0x74;
}
'@

$p = Get-Process electron |
  Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero -and ($_.MainWindowTitle -match 'Squirrel|归仓|推荐|视频|历史' -or $_.Id -eq 56572) } |
  Select-Object -First 1
if (-not $p) { throw 'No Squirrel window' }
[void][KeySend]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep -Milliseconds 200
# Ctrl+R
[KeySend]::keybd_event([KeySend]::VK_CONTROL, 0, 0, [UIntPtr]::Zero)
[KeySend]::keybd_event([KeySend]::VK_R, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 40
[KeySend]::keybd_event([KeySend]::VK_R, 0, [KeySend]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
[KeySend]::keybd_event([KeySend]::VK_CONTROL, 0, [KeySend]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 2200
Write-Output ("reloaded pid={0} title={1}" -f $p.Id, $p.MainWindowTitle)
