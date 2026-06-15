# World Cup Broadcast - One-time Setup Script
# Run this in PowerShell as Administrator for Task Scheduler integration.

$ErrorActionPreference = "Stop"
$ProjectDir = "D:\works\test20260615"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  世界杯比分播报 - 一键安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Install Python dependencies
Write-Host "[1/3] 安装 Python 依赖..." -ForegroundColor Yellow
pip install edge-tts
Write-Host "  edge-tts 安装完成" -ForegroundColor Green
Write-Host ""

# 2. Generate sample audio to verify everything works
Write-Host "[2/3] 生成测试语音..." -ForegroundColor Yellow
python "$ProjectDir\worldcup_broadcast.py" --sample
Write-Host "  测试语音生成完成" -ForegroundColor Green
Write-Host ""

# 3. Register Windows Task Scheduler job (daily at 7:00 AM)
Write-Host "[3/3] 注册每日定时任务 (每天早上7:00)..." -ForegroundColor Yellow

$TaskName = "WorldCupBroadcast"
$ScriptPath = "$ProjectDir\worldcup_broadcast.py"
$PythonExe = (Get-Command python).Source

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScriptPath`""
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
    -Description "每天早上7点播报世界杯比分"

Write-Host "  定时任务已注册: 每天早上 07:00" -ForegroundColor Green
Write-Host ""

# 4. Register web server auto-start task (at system startup)
Write-Host "[附加] 注册 Web 服务器开机自启动..." -ForegroundColor Yellow

$WebServerTaskName = "WorldCupWebServer"
$WebServerScript = "$ProjectDir\web_server.py"

$WebAction = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$WebServerScript`""
$WebTrigger = New-ScheduledTaskTrigger -AtStartup
$WebPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited
$WebSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartInterval (New-TimeSpan -Minutes 5) -RestartCount 999

Unregister-ScheduledTask -TaskName $WebServerTaskName -ErrorAction SilentlyContinue -Confirm:$false

Register-ScheduledTask -TaskName $WebServerTaskName `
    -Action $WebAction `
    -Trigger $WebTrigger `
    -Principal $WebPrincipal `
    -Settings $WebSettings `
    -Description "世界杯播报 Web 服务器 (开机自启)"

Write-Host "  Web 服务器已设置为开机自启" -ForegroundColor Green
Write-Host ""

# Summary
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -notlike "*Loopback*" -and $_.PrefixOrigin -ne "WellKnown"
} | Select-Object -First 1).IPAddress

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  手机访问地址: http://${ip}:8888" -ForegroundColor Yellow
Write-Host "  播报时间:     每天早上 07:00" -ForegroundColor Yellow
Write-Host ""
Write-Host "  手动测试: python `"$ProjectDir\worldcup_broadcast.py`" --sample" -ForegroundColor Gray
Write-Host "  启动服务: python `"$ProjectDir\web_server.py`"" -ForegroundColor Gray
Write-Host ""
