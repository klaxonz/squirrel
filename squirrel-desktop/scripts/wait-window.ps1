$ErrorActionPreference = 'SilentlyContinue'
for ($i = 0; $i -lt 40; $i++) {
  $p = Get-Process electron | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } | Select-Object -First 1
  if ($p) {
    Write-Output ("ready pid={0} title={1}" -f $p.Id, $p.MainWindowTitle)
    exit 0
  }
  Start-Sleep -Seconds 1
}
Write-Output 'no window'
exit 1
