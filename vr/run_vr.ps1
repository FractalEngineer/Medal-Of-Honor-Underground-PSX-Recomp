param(
    [ValidateSet('current', 'vdxr', 'oculus', 'steamvr')]
    [string]$Runtime = 'current',
    [string]$RuntimeJson = '',
    [string]$BuildDirectory = 'build-release',
    [ValidateRange(-1, 99)]
    [int]$Slot = 2,
    [ValidateRange(1, 65536)]
    [double]$UnitsPerMeter = (48.0 / 0.067),
    [ValidateRange(0.25, 20)]
    [double]$MenuDistance = 2,
    [ValidateRange(0.25, 10)]
    [double]$MenuWidth = 2,
    [string]$GameConfig = '',
    [string]$MemcardDirectory = '',
    [string]$LogDirectory = 'analysis\vr-baseline',
    [int]$Seconds = 0,
    [ValidateRange(1, 120)]
    [int]$StartupTimeoutSeconds = 30,
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$buildPath = Join-Path $repoRoot $BuildDirectory
$exePath = Join-Path $buildPath 'Medal_of_Honor_Underground_Recompiled.exe'
$logPath = Join-Path $repoRoot $LogDirectory
$stdoutLog = Join-Path $logPath 'vr-launch.stdout.log'
$stderrLog = Join-Path $logPath 'vr-launch.stderr.log'
$readyPath = Join-Path ([IO.Path]::GetTempPath()) ('mohu-vr-ready-' + [guid]::NewGuid().ToString('N') + '.json')
$process = $null
$savedEnvironment = @{}

function Resolve-RuntimeManifest {
    param([string]$Name, [string]$ExplicitPath)

    if ($ExplicitPath) {
        if (-not (Test-Path -LiteralPath $ExplicitPath)) {
            throw "OpenXR runtime manifest not found: $ExplicitPath"
        }
        return (Resolve-Path -LiteralPath $ExplicitPath).Path
    }
    if (-not $Name -or $Name -eq 'current') {
        return $null
    }

    $candidates = @()
    if ($Name -eq 'vdxr') {
        if ($env:ProgramFiles) {
            $candidates += Join-Path $env:ProgramFiles 'Virtual Desktop Streamer\OpenXR\virtualdesktop-openxr.json'
        }
        if (${env:ProgramFiles(x86)}) {
            $candidates += Join-Path ${env:ProgramFiles(x86)} 'Virtual Desktop Streamer\OpenXR\virtualdesktop-openxr.json'
        }
        if ($env:LOCALAPPDATA) {
            $candidates += Join-Path $env:LOCALAPPDATA 'Programs\VirtualDesktopStreamer\OpenXR\virtualdesktop-openxr.json'
        }
    } elseif ($Name -eq 'oculus') {
        if ($env:ProgramFiles) {
            $candidates += Join-Path $env:ProgramFiles 'Meta Horizon\Support\oculus-runtime\oculus_openxr_64.json'
            $candidates += Join-Path $env:ProgramFiles 'Oculus\Support\oculus-runtime\oculus_openxr_64.json'
        }
    } elseif ($Name -eq 'steamvr') {
        if (${env:ProgramFiles(x86)}) {
            $candidates += Join-Path ${env:ProgramFiles(x86)} 'Steam\steamapps\common\SteamVR\steamxr_win64.json'
        }
        if ($env:ProgramFiles) {
            $candidates += Join-Path $env:ProgramFiles 'Steam\steamapps\common\SteamVR\steamxr_win64.json'
        }
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "No $Name OpenXR runtime manifest found. Tried: $($candidates -join '; ')"
}

function Resolve-OpenXrSource {
    if ($env:PSX_OPENXR_SDK_SOURCE_DIR) {
        return (Resolve-Path -LiteralPath $env:PSX_OPENXR_SDK_SOURCE_DIR).Path
    }
    $siblingReference = Join-Path (Split-Path $repoRoot -Parent) 'Medal-Of-Honor-PSX-Recomp\build-release\_deps\psx_openxr_sdk-src'
    $candidates = @(
        (Join-Path $buildPath '_deps\psx_openxr_sdk-src'),
        $siblingReference
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Build-Release {
    $webpSource = Join-Path $buildPath '_deps\psx_libwebp-src'
    if (-not (Test-Path -LiteralPath $webpSource)) {
        $webpSource = Join-Path $repoRoot 'build-release\_deps\psx_libwebp-src'
    }
    if (Test-Path -LiteralPath $webpSource) {
        $env:PSX_LIBWEBP_SOURCE_DIR = (Resolve-Path -LiteralPath $webpSource).Path
    } else {
        Write-Warning 'Pre-fetched libwebp source is unavailable; CMake will try the pinned fetch.'
    }
    $openXrSource = Resolve-OpenXrSource
    if ($openXrSource) {
        $env:PSX_OPENXR_SDK_SOURCE_DIR = $openXrSource
    } else {
        Write-Warning 'Pre-fetched OpenXR SDK source is unavailable; CMake will try the pinned fetch.'
    }
    cmake -S $repoRoot -B $buildPath `
        -DCMAKE_BUILD_TYPE=Release `
        -DMOHU_VR_DIAGNOSTICS=ON `
        -DPSX_OPENXR=ON `
        -DPSX_DEBUG_TOOLS=OFF `
        -DPSXRECOMP_REQUIRE_GAME_C=ON
    if ($LASTEXITCODE -ne 0) {
        throw 'Release configure failed.'
    }
    cmake --build $buildPath --target psx-runtime -- -j 8
    if ($LASTEXITCODE -ne 0) {
        throw 'Release build failed.'
    }
}

if ($Seconds -lt 0) {
    throw '-Seconds must be zero or positive.'
}
if (-not $GameConfig) {
    $diagnosticConfig = Join-Path $repoRoot 'analysis\vr-baseline\game-interp.toml'
    $GameConfig = if (Test-Path -LiteralPath $diagnosticConfig) { $diagnosticConfig } else { Join-Path $repoRoot 'game.toml' }
}
if (-not $MemcardDirectory) {
    $diagnosticSaves = Join-Path $repoRoot 'analysis\vr-baseline\saves'
    if (Test-Path -LiteralPath $diagnosticSaves) {
        $MemcardDirectory = $diagnosticSaves
    }
}
$GameConfig = (Resolve-Path -LiteralPath $GameConfig).Path
if ($MemcardDirectory) {
    $MemcardDirectory = (Resolve-Path -LiteralPath $MemcardDirectory).Path
}
$runtimeManifest = Resolve-RuntimeManifest -Name $Runtime -ExplicitPath $RuntimeJson
[IO.Directory]::CreateDirectory($logPath) | Out-Null

Push-Location $repoRoot
try {
    if ($Build) {
        Build-Release
    }
    if (-not (Test-Path -LiteralPath $exePath)) {
        throw "Game executable missing: $exePath. Run this launcher with -Build first."
    }

    $environment = @{
        PSX_OPENXR = $null
        PSX_OPENXR_ENABLE = '1'
        MOHU_VR_OPENXR = '1'
        MOHU_VR_UNITS_PER_METER = $UnitsPerMeter.ToString([Globalization.CultureInfo]::InvariantCulture)
        MOHU_VR_MENU_DISTANCE = $MenuDistance.ToString([Globalization.CultureInfo]::InvariantCulture)
        MOHU_VR_MENU_WIDTH = $MenuWidth.ToString([Globalization.CultureInfo]::InvariantCulture)
        PSX_STEREO_SHED = '0'
        PSX_DITHERING = '0'
        PSX_INTERNAL_RESOLUTION = 'native'
        PSX_OPENXR_READY_FILE = $readyPath
    }
    if ($null -ne $runtimeManifest) {
        $environment.XR_RUNTIME_JSON = $runtimeManifest
    }
    if ($Slot -ge 0) {
        $environment.PSX_LOAD_SLOT = [string]$Slot
    }
    foreach ($key in $environment.Keys) {
        $savedEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $environment[$key], 'Process')
    }

    $arguments = '--game "{0}" --no-launcher' -f $GameConfig
    if ($MemcardDirectory) {
        $arguments += ' --memcard-dir "{0}"' -f $MemcardDirectory
    }
    $process = Start-Process -FilePath $exePath -ArgumentList $arguments `
        -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog

    $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    $receipt = $null
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($process.HasExited) {
            throw "Game exited during VR startup with code $($process.ExitCode)."
        }
        if (Test-Path -LiteralPath $readyPath) {
            try {
                $receipt = Get-Content -LiteralPath $readyPath -Raw | ConvertFrom-Json
            } catch {
                $receipt = $null
            }
        }
        if ($receipt -and -not $receipt.ready) {
            throw "VR slot load failed: $($receipt.savestate | ConvertTo-Json -Compress)"
        }
        if ($receipt -and $receipt.openxr.running -and $receipt.openxr.submitted -gt 0) {
            break
        }
        Start-Sleep -Milliseconds 200
    }
    if (-not $receipt -or -not $receipt.openxr.running -or $receipt.openxr.submitted -le 0) {
        throw 'VR startup did not submit a headset frame. Start the selected OpenXR runtime first.'
    }
    Write-Host "VR active. Runtime: $Runtime; submitted frames: $($receipt.openxr.submitted)"

    if ($Seconds -gt 0) {
        $null = $process.WaitForExit($Seconds * 1000)
    } else {
        $process.WaitForExit()
    }
} catch {
    if (Test-Path -LiteralPath $stderrLog) {
        Write-Host '--- runtime stderr ---'
        Get-Content -LiteralPath $stderrLog -Tail 30
    }
    if (Test-Path -LiteralPath $stdoutLog) {
        Write-Host '--- runtime stdout ---'
        Get-Content -LiteralPath $stdoutLog -Tail 30
    }
    throw
} finally {
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $process.WaitForExit()
    }
    foreach ($key in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($key, $savedEnvironment[$key], 'Process')
    }
    Remove-Item -LiteralPath $readyPath -Force -ErrorAction SilentlyContinue
    Pop-Location
}
