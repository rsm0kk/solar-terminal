# publish.ps1 — 이 폴더(OneDrive 마스터)를 GitHub 저장소 사본에 동기화하고 푸시한다.
#
#   .\publish.ps1                      # 변경분 커밋·푸시
#   .\publish.ps1 -Message "어댑터 추가"
#
# 왜 별도 사본인가: OneDrive 동기화가 .git 을 잠가서 저장소를 OneDrive 안에 둘 수 없다.
# 그래서 C:\Users\rsm86\<저장소명> 에 사본을 두고 robocopy 로 미러링한다.
# 데이터 수집은 GitHub Actions 가 매일 06:30 KST 에 직접 하므로,
# 이 스크립트는 **코드·설정·수기입력 CSV 를 고쳤을 때만** 돌리면 된다.

param([string]$Message = "")
# "Stop" 을 쓰면 PowerShell 5.1 에서 git 이 stderr 로 내는 진행 메시지까지 예외로 잡힌다.
# 성공·실패는 아래에서 $LASTEXITCODE 로 직접 판단한다.
$ErrorActionPreference = "Continue"

$Src    = $PSScriptRoot
$Repo   = "C:\Users\rsm86\solar-terminal"
$Remote = "https://github.com/rsm0kk/solar-terminal.git"
$Branch = "main"

# 저장소에 절대 들어가면 안 되는 것 (폴더 / 파일)
#  - raw/.cache/history/processed/out/public : Actions 가 캐시로 잇는 생성물
#  - manual 은 제외하지 않는다 — 수기입력 CSV 는 Actions 도 읽어야 한다
$ExcludeDirs  = @(".git", ".claude", "raw", ".cache", "history", "processed", "out", "public",
                  "__pycache__", ".pytest_cache", ".venv", "venv")
$ExcludeFiles = @("secrets.json", ".env", "index.html", "*.pyc", "*.corrupt-*.parquet")

# ---- 1. 사본 준비 ----
if (-not (Test-Path (Join-Path $Repo ".git"))) {
    Write-Host "저장소 사본이 없어 복제합니다: $Repo"
    git clone $Remote $Repo
    if ($LASTEXITCODE -ne 0) { throw "git clone 실패" }
}
Push-Location $Repo
try {
    git fetch origin 2>$null | Out-Null
    $hasRemote = (git ls-remote --heads origin $Branch 2>$null) -ne $null
    if ($hasRemote) {
        git checkout -q -B $Branch "origin/$Branch"
        git reset -q --hard "origin/$Branch"
    } else {
        git checkout -q -B $Branch
    }
    # 커밋 작성자 — 이 사본에만 설정한다 (전역 설정은 건드리지 않는다).
    # 이메일은 GitHub noreply 주소를 써서 공개 저장소에 실제 메일이 노출되지 않게 한다.
    if (-not (git config user.email)) {
        $login = gh api user --jq .login
        $uid   = gh api user --jq .id
        git config user.name  $login
        git config user.email "$uid+$login@users.noreply.github.com"
    }
    git config core.autocrlf false     # LF 그대로 유지 (경고 억제, Actions 와 동일 바이트)
} finally { Pop-Location }

# ---- 2. 미러링 ----
$rc = @($Src, $Repo, "/MIR", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:2", "/W:2",
        "/XD") + $ExcludeDirs + @("/XF") + $ExcludeFiles
robocopy @rc | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy 실패 (코드 $LASTEXITCODE)" }

# ---- 3. 키 유출 검사 ----
# 키는 전력기기 폴더의 secrets.json(공유) 과 이 폴더의 .env 에 있을 수 있다.
$vals = @()
foreach ($p in @((Join-Path $Src "..\전력기기 대쉬보드\secrets.json"), (Join-Path $Src ".env"))) {
    if (-not (Test-Path $p)) { continue }
    if ($p -like "*.json") {
        $vals += (Get-Content $p -Raw | ConvertFrom-Json).PSObject.Properties.Value
    } else {
        $vals += Get-Content $p | Where-Object { $_ -match "=" -and $_ -notmatch "^\s*#" } |
                 ForEach-Object { ($_ -split "=", 2)[1].Trim().Trim('"').Trim("'") }
    }
}
$vals = $vals | Where-Object { $_ -and $_.Length -ge 12 } | ForEach-Object { $_.Substring(0, 12) } | Select-Object -Unique
if ($vals) {
    $hits = Get-ChildItem $Repo -Recurse -File | Where-Object { $_.FullName -notmatch "\\\.git\\" } |
            Select-String -Pattern $vals -SimpleMatch -List
    if ($hits) {
        $hits | ForEach-Object { Write-Host "  키 발견: $($_.Path)" -ForegroundColor Red }
        throw "API 키가 사본에 들어 있습니다. 푸시를 중단합니다."
    }
}

# ---- 4. 커밋·푸시 ----
Push-Location $Repo
try {
    git add -A
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "변경 없음 — 푸시할 것이 없습니다."
    } else {
        if (-not $Message) { $Message = "sync $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
        git commit -q -m $Message
        git push -u origin $Branch
        if ($LASTEXITCODE -ne 0) { throw "git push 실패" }
        Write-Host "푸시 완료 → https://github.com/rsm0kk/solar-terminal"
        Write-Host "Actions 가 빌드하면 https://rsm0kk.github.io/solar-terminal/ 에 반영됩니다 (5~10분)."
    }
} finally { Pop-Location }
