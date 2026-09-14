# 태양광 대시보드 로컬 갱신 (Windows)
#
# 더블클릭 실행하거나 작업 스케줄러에 등록해서 씁니다.
#   powershell -ExecutionPolicy Bypass -File "scripts\run_local_update.ps1"
#
# 작업 스케줄러 등록:
#   작업 스케줄러 → 작업 만들기 → 트리거: 매일 06:30
#   동작: 프로그램 시작
#     프로그램:  powershell.exe
#     인수:      -ExecutionPolicy Bypass -File "scripts\run_local_update.ps1"
#     시작 위치: 이 프로젝트 폴더 경로

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "==============================================="
Write-Host "  태양광 대시보드 갱신  $stamp"
Write-Host "==============================================="

# 파이썬 확인
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[오류] python 을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "python.org 에서 설치하되 'Add Python to PATH' 를 반드시 체크하세요."
    Read-Host "엔터를 누르면 종료"
    exit 1
}

# 의존성 확인 (없으면 설치)
python -c "import pandas, requests, pydantic, yaml, pyarrow" 2>$null
if (-not $?) {
    Write-Host "[안내] 필요한 패키지를 설치합니다..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt --quiet --disable-pip-version-check
}

# 수집 및 빌드
python scripts\update_all.py
$code = $LASTEXITCODE

# 로그 보관
$logDir = Join-Path $root "data\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
"$stamp  exit=$code" | Add-Content -Path (Join-Path $logDir "update.log") -Encoding utf8

if ($code -eq 0) {
    Write-Host ""
    Write-Host "완료. 산출물:" -ForegroundColor Green
    Write-Host "  out\태양광_대시보드_최신.html   <- 이 파일을 열거나 공유하세요"
    Write-Host "  public\data\*.json"
    $html = Join-Path $root "out\태양광_대시보드_최신.html"
    if (Test-Path $html) { Start-Process $html }
} else {
    Write-Host ""
    Write-Host "[경고] 일부 핵심 소스 수집에 실패했습니다 (exit=$code)." -ForegroundColor Yellow
    Write-Host "생성된 HTML 의 '데이터 상태' 탭에서 원인을 확인하세요."
}

if ($Host.Name -eq "ConsoleHost" -and -not $env:CI) { Read-Host "엔터를 누르면 종료" }
exit $code
