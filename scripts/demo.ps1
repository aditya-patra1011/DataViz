<#
Gets DataViz ready for a demo: starts the virtual phone, installs the app, copies the sample
CSV files onto the phone and opens the app.

Run it from the DataViz folder:
    powershell -ExecutionPolicy Bypass -File scripts\demo.ps1

Options:
    -Rebuild        build the app again first (after changing the code)
    -SafeGraphics   draw the phone screen in software, if the phone window stays black
#>
param([switch]$Rebuild, [switch]$SafeGraphics)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$sdk = "$env:LOCALAPPDATA\Android\Sdk"
$adb = "$sdk\platform-tools\adb.exe"
$emulator = "$sdk\emulator\emulator.exe"
$phone = "DataViz_Phone"
$apk = "$root\android\app\build\outputs\apk\emulator\release\app-emulator-release.apk"

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }

# adb prints progress on the error stream, which PowerShell would show as errors
function Adb {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $adb @args 2>&1 | Out-Null } finally { $ErrorActionPreference = $previous }
}

# Same, but returns what adb printed, ignoring errors such as "device offline" while starting
function AdbText {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { "$(& $adb @args 2>$null)".Trim() } finally { $ErrorActionPreference = $previous }
}

if (-not (Test-Path $adb)) {
    throw "The Android SDK was not found at $sdk. Install Android Studio first."
}

if ($Rebuild -or -not (Test-Path $apk)) {
    Step "Building the app (the first build takes several minutes)"
    $jdk = Get-ChildItem "$env:USERPROFILE\.jdks" -Filter "jdk-17*" | Select-Object -First 1
    if (-not $jdk) { throw "Java 17 was not found in $env:USERPROFILE\.jdks." }
    $env:JAVA_HOME = $jdk.FullName
    Push-Location "$root\android"
    try {
        & .\gradlew.bat assembleEmulatorRelease --console=plain
        if ($LASTEXITCODE -ne 0) { throw "The build failed. See the messages above." }
    } finally {
        Pop-Location
    }
}

$started = $null
if ((AdbText devices) -notmatch "emulator-\d+\s+device") {
    Step "Starting the virtual phone"
    # A fresh start every time is slower than resuming, but never brings back a stuck screen
    $options = @("-avd", $phone, "-no-snapshot")
    if ($SafeGraphics) { $options += @("-gpu", "swiftshader_indirect") }
    $started = Start-Process $emulator -ArgumentList $options -PassThru
}

Step "Waiting for the phone to finish starting (usually 1 to 3 minutes)"
$deadline = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Seconds 3
    if ($started -and $started.HasExited) {
        throw "The phone window closed before it finished starting. Run this script again."
    }
    if ((Get-Date) -gt $deadline) {
        throw "The phone took too long to start. Close it and run this script again, " +
            "adding -SafeGraphics if the window stays black."
    }
    $booted = AdbText shell getprop sys.boot_completed
} until ($booted -eq "1")

# Right after starting, Android keeps working in the background for a few minutes, and the
# phone can show "System UI isn't responding". Wait until it has calmed down.
Step "Letting the phone finish its start-up work (up to 5 minutes)"
$settleBy = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Seconds 5
    $load = [double]::Parse((AdbText shell cat /proc/loadavg).Split(" ")[0],
        [System.Globalization.CultureInfo]::InvariantCulture)
} until ($load -lt 4 -or (Get-Date) -gt $settleBy)

Step "Installing DataViz"
Adb install -r $apk
if ($LASTEXITCODE -ne 0) { throw "Installing the app failed." }

Step "Copying the sample CSV files to the phone's Download folder"
foreach ($file in Get-ChildItem "$root\data\samples\*.csv") {
    Adb push $file.FullName "/sdcard/Download/$($file.Name)"
    Adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE `
        -d "file:///sdcard/Download/$($file.Name)"
}

Step "Opening DataViz"
Adb shell am start -n com.adityapatra.dataviz/.MainActivity

Write-Host "`nReady. The first launch takes a few seconds while Python starts." -ForegroundColor Green
