param(
    [ValidateSet('current', 'vdxr', 'oculus', 'steamvr')]
    [string]$Runtime = 'current',
    [string]$RuntimeJson = '',
    [string]$BuildDirectory = 'build-release',
    [ValidateRange(-1, 99)]
    [int]$Slot = 2,
    [ValidateRange(40, 80)]
    [double]$IpdMm = 67,
    [ValidateRange(0.05, 20)]
    [double]$WorldScale = 3,
    [ValidateSet('native', '720p', '1080p', '1440p', '4k', '5k', '8k', 'display')]
    [string]$InternalResolution = '1080p',
    [double]$UnitsPerMeter = 0,
    [ValidateRange(0.25, 20)]
    [double]$MenuDistance = 2,
    [ValidateRange(0.25, 10)]
    [double]$MenuWidth = 2,
    [string]$GameConfig = '',
    [string]$MemcardDirectory = '',
    [string]$LogDirectory = 'analysis\vr-baseline',
    [ValidateRange(0, 65535)]
    [int]$DebugPort = 0,
    [int]$Seconds = 0,
    [ValidateRange(1, 120)]
    [int]$StartupTimeoutSeconds = 30,
    [switch]$Headless,
    [switch]$NoHeadFrustumDiagnostic,
    [switch]$KeepFlatHud,
    [switch]$NoMovement,
    [ValidateRange(0, 0.9)]
    [double]$MoveDeadzone = 0.2,
    [ValidateRange(0, 2)]
    [double]$TurnGain = 0.65,
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$buildPath = Join-Path $repoRoot $BuildDirectory
$exePath = Join-Path $buildPath 'Medal_of_Honor_Underground_Recompiled.exe'
$logPath = if ([IO.Path]::IsPathRooted($LogDirectory)) { $LogDirectory } else { Join-Path $repoRoot $LogDirectory }
$stdoutLog = Join-Path $logPath 'vr-launch.stdout.log'
$stderrLog = Join-Path $logPath 'vr-launch.stderr.log'
$readyPath = Join-Path ([IO.Path]::GetTempPath()) ('mohu-vr-ready-' + [guid]::NewGuid().ToString('N') + '.json')
$process = $null
$savedEnvironment = @{}
$steamVrSettings = $null
$steamVrOriginal = $null
$steamVrStarted = $false

function Get-StereoProof {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    $line = Get-Content -LiteralPath $Path -Tail 200 |
        Where-Object { $_ -match '^mohu-vr-diag: stereo_proof ' } |
        Select-Object -Last 1
    if (-not $line) {
        return $null
    }
    $pattern = 'attempt=(?<attempt>\d+) pairs=(?<pairs>\d+) ' +
        'rendered=(?<rendered>\d+).*xr_begin_failures=(?<begin>\d+) ' +
        'xr_view_failures=(?<view>\d+) xr_ends=(?<ends>\d+)'
    $match = [regex]::Match([string]$line, $pattern)
    if (-not $match.Success) {
        return $null
    }
    [pscustomobject]@{
        attempt = [int]$match.Groups['attempt'].Value
        pairs = [int]$match.Groups['pairs'].Value
        rendered = [int]$match.Groups['rendered'].Value
        begin_failures = [int]$match.Groups['begin'].Value
        view_failures = [int]$match.Groups['view'].Value
        ends = [int]$match.Groups['ends'].Value
        line = [string]$line
    }
}

function Wait-StereoProof {
    param([string]$Path, [int]$TimeoutSeconds = 30, [int]$AfterPairs = 0)

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $proof = Get-StereoProof -Path $Path
        if ($proof -and $proof.attempt -gt 0 -and $proof.pairs -gt 0 -and
            $proof.rendered -eq 1 -and $proof.pairs -eq $proof.attempt -and
            $proof.begin_failures -eq 0 -and $proof.view_failures -eq 0 -and
            $proof.pairs -gt $AfterPairs) {
            return $proof
        }
        Start-Sleep -Milliseconds 250
    }
    throw "No complete OpenXR stereo pair appeared within $TimeoutSeconds seconds."
}

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

function Resolve-SteamRoot {
    $candidates = @()
    $registered = (Get-ItemProperty -Path 'HKCU:\SOFTWARE\Valve\Steam' `
        -Name SteamPath -ErrorAction SilentlyContinue).SteamPath
    if ($registered) {
        $candidates += $registered
    }
    if (${env:ProgramFiles(x86)}) {
        $candidates += Join-Path ${env:ProgramFiles(x86)} 'Steam'
    }
    if ($env:ProgramFiles) {
        $candidates += Join-Path $env:ProgramFiles 'Steam'
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $candidate 'steamapps\common\SteamVR')) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw 'Steam installation with SteamVR was not found.'
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
$baseUnitsPerMeter = if ($UnitsPerMeter -gt 0) {
    $UnitsPerMeter
} else {
    48.0 / ($IpdMm / 1000.0)
}
if ($baseUnitsPerMeter -lt 1 -or $baseUnitsPerMeter -gt 65536) {
    throw 'Base units per meter must be between 1 and 65536.'
}
$effectiveUnitsPerMeter = $baseUnitsPerMeter / $WorldScale
if ($effectiveUnitsPerMeter -lt 1 -or $effectiveUnitsPerMeter -gt 65536) {
    throw 'World scale produced units per meter outside 1..65536.'
}
if ($Headless -and $RuntimeJson) {
    throw '-Headless drives SteamVR; do not also pass -RuntimeJson.'
}
if ($Headless) {
    $Runtime = 'steamvr'
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
    Write-Host (
        'VR profile: IPD={0}mm world_scale={1} units_per_meter={2} resolution={3} head_frustum={4} flat_hud={5}' -f
        $IpdMm,
        $WorldScale,
        $effectiveUnitsPerMeter.ToString([Globalization.CultureInfo]::InvariantCulture),
        $InternalResolution,
        $(if ($NoHeadFrustumDiagnostic) { '0' } else { '1' }),
        $(if ($KeepFlatHud) { '0' } else { '1' })
    )

    if ($Headless) {
        $steamRoot = Resolve-SteamRoot
        $steamVrRoot = Join-Path $steamRoot 'steamapps\common\SteamVR'
        $steamVrStartup = Join-Path $steamVrRoot 'bin\win64\vrstartup.exe'
        $steamVrSettings = Join-Path $steamRoot 'config\steamvr.vrsettings'
        if (-not (Test-Path -LiteralPath $steamVrStartup)) {
            throw "SteamVR startup executable not found: $steamVrStartup"
        }
        if (-not (Test-Path -LiteralPath $steamVrSettings)) {
            throw "SteamVR settings not found: $steamVrSettings"
        }
        if (Get-Process vrserver,vrcompositor,vrmonitor,vrdashboard,vrwebhelper `
                -ErrorAction SilentlyContinue) {
            throw 'SteamVR is already running. Close it before -Headless.'
        }

        $steamVrOriginal = [IO.File]::ReadAllText($steamVrSettings)
        $steamVrNullSettings = python (Join-Path $PSScriptRoot 'headless_steamvr.py') `
            --settings $steamVrSettings
        if ($LASTEXITCODE -ne 0) {
            throw 'Cannot prepare SteamVR null-HMD settings.'
        }
        [IO.File]::WriteAllText(
            $steamVrSettings,
            (($steamVrNullSettings -join "`n") + "`n"),
            (New-Object Text.UTF8Encoding($false))
        )
        Start-Process -FilePath $steamVrStartup -WindowStyle Hidden | Out-Null
        $steamVrStarted = $true
        $steamVrDeadline = (Get-Date).AddSeconds(60)
        while ((Get-Date) -lt $steamVrDeadline) {
            if ((Get-Process vrserver -ErrorAction SilentlyContinue) -and
                (Get-Process vrcompositor -ErrorAction SilentlyContinue)) {
                break
            }
            Start-Sleep -Milliseconds 500
        }
        if (-not (Get-Process vrcompositor -ErrorAction SilentlyContinue)) {
            throw 'SteamVR did not start with the null HMD. Check SteamVR logs.'
        }
        Write-Host 'SteamVR is up on the null HMD (no headset required).'
    }

    $environment = @{
        PSX_LOAD_SLOT = $(if ($Slot -ge 0) { [string]$Slot } else { $null })
        PSX_OPENXR = $null
        PSX_OPENXR_ENABLE = '1'
        MOHU_VR_OPENXR = '1'
        MOHU_VR_UNITS_PER_METER = $effectiveUnitsPerMeter.ToString([Globalization.CultureInfo]::InvariantCulture)
        MOHU_VR_MENU_DISTANCE = $MenuDistance.ToString([Globalization.CultureInfo]::InvariantCulture)
        MOHU_VR_MENU_WIDTH = $MenuWidth.ToString([Globalization.CultureInfo]::InvariantCulture)
        PSX_FRAME_REPORT_MS = '1000'
        PSX_STEREO_SHED = '0'
        PSX_VSYNC = '0'
        PSX_DITHERING = '0'
        PSX_INTERNAL_RESOLUTION = $InternalResolution
        PSX_VR_HEAD_FRUSTUM = $(if ($NoHeadFrustumDiagnostic) { '0' } else { '1' })
        PSX_VR_SUPPRESS_FLAT_HUD = $(if ($KeepFlatHud) { '0' } else { '1' })
        PSX_VR_MOVEMENT = $(if ($NoMovement) { '0' } else { '1' })
        PSX_VR_MOVE_DEADZONE = $MoveDeadzone.ToString([Globalization.CultureInfo]::InvariantCulture)
        PSX_VR_TURN_GAIN = $TurnGain.ToString([Globalization.CultureInfo]::InvariantCulture)
        PSX_OPENXR_READY_FILE = $readyPath
    }
    if ($null -ne $runtimeManifest) {
        $environment.XR_RUNTIME_JSON = $runtimeManifest
    }
    foreach ($key in $environment.Keys) {
        $savedEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $environment[$key], 'Process')
    }

    $arguments = '--game "{0}" --no-launcher' -f $GameConfig
    if ($MemcardDirectory) {
        $arguments += ' --memcard-dir "{0}"' -f $MemcardDirectory
    }
    if ($DebugPort -gt 0) {
        $arguments += ' --debug-port {0}' -f $DebugPort
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
    Copy-Item -LiteralPath $readyPath -Destination (Join-Path $logPath 'startup.json') -Force
    if ($Slot -ge 0) {
        $proofFirst = Wait-StereoProof -Path $stdoutLog
        Start-Sleep -Seconds 2
        $proofSecond = Wait-StereoProof -Path $stdoutLog -TimeoutSeconds 5 -AfterPairs $proofFirst.pairs
        if ($proofSecond.pairs -le $proofFirst.pairs) {
            throw 'Stereo proof counters did not advance during the smoke interval.'
        }
        [pscustomobject]@{
            receipt = $receipt
            first = $proofFirst
            second = $proofSecond
            new_pairs = $proofSecond.pairs - $proofFirst.pairs
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (
            Join-Path $logPath 'openxr-smoke.json'
        ) -Encoding utf8
        Write-Host (
            'VR active. Runtime: {0}; complete pairs in 2s: {1}; xr failures: {2}' -f
            $Runtime,
            ($proofSecond.pairs - $proofFirst.pairs),
            ($proofSecond.begin_failures + $proofSecond.view_failures)
        )
    } else {
        Write-Host 'VR native menu active. No save slot loaded; stereo starts on a supported gameplay frame.'
    }

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
    if ($Headless -and $steamVrStarted) {
        Get-Process vrserver,vrcompositor,vrmonitor,vrdashboard,vrwebhelper `
            -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        $steamVrDeadline = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $steamVrDeadline -and
            (Get-Process vrserver,vrcompositor,vrmonitor,vrdashboard,vrwebhelper `
                -ErrorAction SilentlyContinue)) {
            Start-Sleep -Milliseconds 500
        }
    }
    if ($steamVrSettings -and $steamVrOriginal) {
        $restored = $false
        $restoreDeadline = (Get-Date).AddSeconds(15)
        $restoreError = $null
        while ((Get-Date) -lt $restoreDeadline -and -not $restored) {
            try {
                [IO.File]::WriteAllText(
                    $steamVrSettings,
                    $steamVrOriginal,
                    (New-Object Text.UTF8Encoding($false))
                )
                $restored = $true
            } catch {
                $restoreError = $_.Exception.Message
                Start-Sleep -Milliseconds 500
            }
        }
        if (-not $restored) {
            $backupPath = Join-Path $logPath 'steamvr.vrsettings.pre-headless'
            [IO.File]::WriteAllText(
                $backupPath,
                $steamVrOriginal,
                (New-Object Text.UTF8Encoding($false))
            )
            Write-Warning (
                "Could not restore SteamVR settings ($restoreError). " +
                "Original settings saved at $backupPath."
            )
        }
    }
    foreach ($key in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($key, $savedEnvironment[$key], 'Process')
    }
    Remove-Item -LiteralPath $readyPath -Force -ErrorAction SilentlyContinue
    Pop-Location
}
