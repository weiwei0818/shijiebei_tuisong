# Stock Market Broadcast - One-time Setup Script
# Run this in PowerShell as Administrator for Task Scheduler integration.

$ErrorActionPreference = "Stop"
$ProjectDir = "D:\works\test20260615"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  每日股市播报 - 一键安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Install Python dependencies
Write-Host "[1/3] 安装 Python 依赖..." -ForegroundColor Yellow
pip install yfinance
Write-Host "  yfinance 安装完成" -ForegroundColor Green
Write-Host ""

# 2. Test the script with sample output
Write-Host "[2/3] 生成测试推送内容..." -ForegroundColor Yellow
python "$ProjectDir\stock_broadcast.py" --sample
Write-Host "  测试内容生成完成" -ForegroundColor Green
Write-Host ""

# 3. Register Windows Task Scheduler job (daily at 7:00 AM)
Write-Host "[3/3] 注册每日定时任务 (每天早上7:00)..." -ForegroundColor Yellow

$TaskName = "StockBroadcast"
$ScriptPath = "$ProjectDir\stock_broadcast.py"
$PythonExe = (Get-Command python).Source

# Remove existing World Cup task if present
Unregister-ScheduledTask -TaskName "WorldCupBroadcast" -ErrorAction SilentlyContinue -Confirm:$false

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScriptPath`" --push"
$Trigger = New-ScheduledTaskTrigger -Daily -At "07:00"
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Remove existing task if present
Unregister-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue -Confirm:$false

Register-ScheduledTask -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "每天早上7点播报美股涨幅榜和A股涨停筛选"

Write-Host "  定时任务已注册: 每天早上 07:00" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  播报时间:     每天早上 07:00" -ForegroundColor Yellow
Write-Host "  推送渠道:     微信 (PushPlus)" -ForegroundColor Yellow
Write-Host ""
Write-Host "  手动测试: python `"$ProjectDir\stock_broadcast.py`" --sample" -ForegroundColor Gray
Write-Host "  手动推送: python `"$ProjectDir\stock_broadcast.py`" --push" -ForegroundColor Gray
Write-Host ""
