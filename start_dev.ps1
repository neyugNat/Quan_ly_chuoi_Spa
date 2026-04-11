param(
    [int]$Port = 5000,
    [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "Khong tim thay .venv\\Scripts\\python.exe" -ForegroundColor Red
    Write-Host "Hay tao/kich hoat virtualenv truoc khi chay." -ForegroundColor Yellow
    exit 1
}

# Xoa DATABASE_URL de tranh tro nham DB ngoai du an.
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue

# Don cac process dang giu cong de restart sach.
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique

foreach ($procId in $listeners) {
    try {
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Write-Host "Da dung process PID $procId dang chiem cong $Port"
    }
    catch {
        Write-Host "Khong the dung PID $procId tren cong ${Port}: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "Khoi dong Flask dev server tai http://${BindHost}:$Port" -ForegroundColor Green
Write-Host "Tu gio chi can Save file, Flask se tu reload." -ForegroundColor Green

& $pythonExe -m flask --app backend.app:create_app --debug run --host $BindHost --port $Port