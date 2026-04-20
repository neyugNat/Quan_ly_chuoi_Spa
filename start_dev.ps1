param(
    [int]$Port = 5000,
    [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
# Tren mot so ban PowerShell, native command exit code != 0 co the bi doi thanh terminating error.
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venvPath = Join-Path $scriptDir ".venv"
$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"

function Resolve-BasePython {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        return @{
            Exe = "py"
            Args = @("-3")
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return @{
            Exe = "python"
            Args = @()
        }
    }

    throw "Khong tim thay Python launcher (py) hoac python trong PATH."
}

if (-not (Test-Path $pythonExe)) {
    Write-Host "Khong tim thay .venv. Dang tao virtualenv..." -ForegroundColor Yellow
    $basePython = Resolve-BasePython
    & $basePython.Exe @($basePython.Args + @("-m", "venv", $venvPath))

    if (-not (Test-Path $pythonExe)) {
        Write-Host "Tao .venv that bai. Vui long kiem tra lai cai dat Python." -ForegroundColor Red
        exit 1
    }
}

$requirementsFile = Join-Path $scriptDir "backend\requirements.txt"
if (-not (Test-Path $requirementsFile)) {
    Write-Host "Khong tim thay backend\\requirements.txt" -ForegroundColor Red
    exit 1
}

& $pythonExe -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('flask') else 1)" 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Chua co Flask trong .venv. Dang cai dependencies..." -ForegroundColor Yellow
    & $pythonExe -m pip install -r $requirementsFile

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Cai dependencies that bai. Vui long kiem tra ket noi mang/pip." -ForegroundColor Red
        exit 1
    }
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