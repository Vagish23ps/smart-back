# ─────────────────────────────────────────────────────────────────────────────
# SmartBack - Windows Startup Setup via Task Scheduler
#
# WHY Task Scheduler instead of the Startup folder?
#   The Startup folder runs programs as standard user (no admin rights),
#   which means keyboard hooks fail silently.
#   Task Scheduler with RunLevel=Highest launches SmartBack as Administrator
#   at every login WITHOUT showing a UAC prompt. This is the correct method.
#
# HOW TO RUN:
#   1. Build the exe first:          build.bat
#   2. Open PowerShell as Admin.
#   3. Run:  .\setup_startup.ps1
#      Or specify custom path:
#      .\setup_startup.ps1 -ExePath "C:\Tools\SmartBack.exe"
# ─────────────────────────────────────────────────────────────────────────────

param(
    [string]$ExePath = "$PSScriptRoot\dist\SmartBack.exe"
)

$TaskName   = "SmartBack"
$TaskDesc   = "SmartBack - Context-aware ESC key remapper (runs at logon with admin rights)"

# ── Verify exe exists ─────────────────────────────────────────────────────────
if (-not (Test-Path $ExePath)) {
    Write-Host ""
    Write-Host "  [ERROR] Executable not found at:" -ForegroundColor Red
    Write-Host "          $ExePath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Run build.bat first to create dist\SmartBack.exe" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "  SmartBack - Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────"
Write-Host "  Exe: $ExePath"
Write-Host ""

# ── Remove existing task (clean reinstall) ────────────────────────────────────
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  Removing existing task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# ── Build task components ─────────────────────────────────────────────────────

# Action: launch SmartBack.exe in its own directory (so relative paths work)
$ExeDir = Split-Path -Parent $ExePath
$Action = New-ScheduledTaskAction `
    -Execute  $ExePath `
    -WorkingDirectory $ExeDir

# Trigger: fire when any user logs on
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Settings
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit      (New-TimeSpan -Seconds 0) `  # No time limit
    -AllowStartIfOnBatteries                           `   # Works on laptops
    -DontStopIfGoingOnBatteries                        `
    -StartWhenAvailable                                `
    -MultipleInstances        IgnoreNew                    # Don't spawn duplicates

# Principal: current user, HIGHEST privileges (= admin without UAC popup)
$Principal = New-ScheduledTaskPrincipal `
    -UserId    "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType  Interactive `
    -RunLevel   Highest

# ── Register the task ─────────────────────────────────────────────────────────
try {
    Register-ScheduledTask `
        -TaskName    $TaskName   `
        -Action      $Action     `
        -Trigger     $Trigger    `
        -Settings    $Settings   `
        -Principal   $Principal  `
        -Description $TaskDesc   `
        -Force | Out-Null

    Write-Host "  [OK] Task registered successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Details:" -ForegroundColor Cyan
    Write-Host "    Task name   : $TaskName"
    Write-Host "    Exe path    : $ExePath"
    Write-Host "    Trigger     : At logon"
    Write-Host "    Run level   : Highest (Administrator)"
    Write-Host "    UAC prompt  : None (suppressed by Task Scheduler)"
    Write-Host ""
    Write-Host "  SmartBack will start automatically on next login." -ForegroundColor Green
    Write-Host "  To start it now, run:  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "  [ERROR] Failed to register task: $_" -ForegroundColor Red
    Write-Host "  Make sure you are running this script as Administrator." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# ── Optionally start right now ────────────────────────────────────────────────
$startNow = Read-Host "  Start SmartBack right now? (y/n)"
if ($startNow -eq 'y' -or $startNow -eq 'Y') {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "  SmartBack started." -ForegroundColor Green
}

Write-Host ""
