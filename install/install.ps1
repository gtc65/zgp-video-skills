# zgp-video-skills 安裝程式（Windows PowerShell）
# 一行安裝：
#   irm https://raw.githubusercontent.com/gtc65/zgp-video-skills/main/install/install.ps1 | iex
# 會做的事：
#   1. 下載本 repo 最新版
#   2. 把三個技能複製到 %USERPROFILE%\.claude\skills\（Claude Code 個人技能）
#   3. 檢查 Python／ffmpeg／Node，並安裝 Python 套件（edge-tts 等）
# 不會動到其他技能；同名技能會被更新成最新版。

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Repo = "gtc65/zgp-video-skills"
$Skills = @("taiwan-narration", "photo-recap-video", "hyperframes-explainer")

Write-Host "== 下載 $Repo ==" -ForegroundColor Cyan
$tmp = Join-Path $env:TEMP ("zgp-video-skills-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force $tmp | Out-Null
$zip = Join-Path $tmp "repo.zip"
Invoke-WebRequest "https://github.com/$Repo/archive/refs/heads/main.zip" -OutFile $zip -UseBasicParsing
Expand-Archive $zip -DestinationPath $tmp -Force
$src = Join-Path (Get-ChildItem $tmp -Directory | Select-Object -First 1).FullName "plugins\school-video\skills"

$dst = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force $dst | Out-Null
foreach ($s in $Skills) {
    $target = Join-Path $dst $s
    if (Test-Path $target) { Remove-Item -Recurse -Force $target }
    Copy-Item -Recurse -Force (Join-Path $src $s) $target
    Write-Host "  已安裝技能：$s" -ForegroundColor Green
}
Remove-Item -Recurse -Force $tmp

Write-Host "`n== 檢查必要軟體 ==" -ForegroundColor Cyan
function Have($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
$py = $null
foreach ($c in @("python", "py")) {
    if (Have $c) {
        try { & $c --version *> $null; if ($LASTEXITCODE -eq 0) { $py = $c; break } } catch {}
    }
}
if ($py) { Write-Host "  Python：OK（$py）" } else { Write-Host "  Python：沒有 → winget install Python.Python.3.13" -ForegroundColor Yellow }
if (Have "ffmpeg") { Write-Host "  ffmpeg：OK" } else { Write-Host "  ffmpeg：沒有 → winget install Gyan.FFmpeg" -ForegroundColor Yellow }
if (Have "node") { Write-Host "  Node：OK（$(node -v)，說明影片需要 v22 以上）" } else { Write-Host "  Node：沒有（只有說明影片需要）→ winget install OpenJS.NodeJS.LTS" -ForegroundColor Yellow }

if ($py) {
    Write-Host "`n== 安裝 Python 套件 ==" -ForegroundColor Cyan
    & $py -m pip install --upgrade edge-tts pillow fonttools brotli numpy mido playwright
    & $py -m playwright install chromium
}

Write-Host "`n完成！重新開啟 Claude Code，問「你有哪些技能？」應該看得到：" -ForegroundColor Green
$Skills | ForEach-Object { Write-Host "  - $_" }
Write-Host "Claude 桌面版（Cowork）／claude.ai 請改用 dist 資料夾的 zip 上傳（見 README）。"
