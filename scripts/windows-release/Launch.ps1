param(
    [ValidateSet('flat', 'current', 'vdxr', 'steamvr', 'oculus')]
    [string]$Runtime = 'flat',
    [string]$DiscPath = '',
    [string]$RuntimeJson = '',
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$exe = Join-Path $root 'Medal_of_Honor_Underground_Recompiled.exe'
$arguments = '--game "{0}" --memcard-dir "{1}"' -f (Join-Path $root 'game.toml'), (Join-Path $root 'saves')
if ($DiscPath) {
    $arguments += ' --disc "{0}"' -f (Resolve-Path -LiteralPath $DiscPath).Path
}

$environment = @{}
foreach ($entry in Get-ChildItem Env:) {
    if ($entry.Name -match '^(MOHU_VR_|PSX_VR_|PSX_OPENXR)' -or
        $entry.Name -in @('PSX_LOAD_SLOT', 'PSX_STEREO_SHED', 'PSX_RENDER_PASS_VERIFY', 'XR_RUNTIME_JSON')) {
        $environment[$entry.Name] = $null
    }
}
$environment.PSX_DEV_INPUT = '0'
if ($Runtime -ne 'flat') {
    $candidates = @()
    if ($RuntimeJson) {
        $candidates += $RuntimeJson
    } elseif ($Runtime -eq 'vdxr') {
        if ($env:ProgramFiles) {
            $candidates += Join-Path $env:ProgramFiles 'Virtual Desktop Streamer\OpenXR\virtualdesktop-openxr.json'
        }
        if (${env:ProgramFiles(x86)}) {
            $candidates += Join-Path ${env:ProgramFiles(x86)} 'Virtual Desktop Streamer\OpenXR\virtualdesktop-openxr.json'
        }
        if ($env:LOCALAPPDATA) {
            $candidates += Join-Path $env:LOCALAPPDATA 'Programs\VirtualDesktopStreamer\OpenXR\virtualdesktop-openxr.json'
        }
    } elseif ($Runtime -eq 'oculus') {
        if ($env:ProgramFiles) {
            $candidates += Join-Path $env:ProgramFiles 'Meta Horizon\Support\oculus-runtime\oculus_openxr_64.json'
            $candidates += Join-Path $env:ProgramFiles 'Oculus\Support\oculus-runtime\oculus_openxr_64.json'
        }
    } elseif ($Runtime -eq 'steamvr') {
        if (${env:ProgramFiles(x86)}) {
            $candidates += Join-Path ${env:ProgramFiles(x86)} 'Steam\steamapps\common\SteamVR\steamxr_win64.json'
        }
        if ($env:ProgramFiles) {
            $candidates += Join-Path $env:ProgramFiles 'Steam\steamapps\common\SteamVR\steamxr_win64.json'
        }
    }
    if ($candidates.Count) {
        $manifest = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
        if (-not $manifest) { throw "No $Runtime OpenXR manifest found. Install/start that runtime, or pass -RuntimeJson." }
        $environment.XR_RUNTIME_JSON = (Resolve-Path -LiteralPath $manifest).Path
    }
    $profile = @{
        PSX_OPENXR_ENABLE = '1'; MOHU_VR_OPENXR = '1'
        MOHU_VR_UNITS_PER_METER = '238.8059701492537'
        MOHU_VR_MENU_DISTANCE = '2'; MOHU_VR_MENU_WIDTH = '2'
        PSX_STEREO_SHED = '0'; PSX_VSYNC = '0'; PSX_DITHERING = '0'
        PSX_INTERNAL_RESOLUTION = '1080p'; PSX_VR_HEAD_FRUSTUM = '1'
        PSX_VR_SUPPRESS_FLAT_HUD = '1'; PSX_VR_WRIST_HUD = '1'
        PSX_VR_MOVEMENT = '1'; PSX_VR_LASER = '1'
        PSX_VR_MOVE_DEADZONE = '0.2'; PSX_VR_TURN_GAIN = '0.65'
        PSX_VR_WEAPON_POSE = '1'; MOHU_VR_WEAPON_CALIBRATED = '1'
        MOHU_VR_WEAPON_AIM = '1'; MOHU_VR_WEAPON_GUN_ONLY = '1'
        MOHU_VR_P38_CALIBRATED = '0'; MOHU_VR_P38_AIM = '0'
        MOHU_VR_FRESH_60 = '0'; MOHU_VR_WORLD_CACHE = '0'
        MOHU_VR_SKIP_NATIVE_WORLD_COPY = '0'
    }
    foreach ($key in $profile.Keys) { $environment[$key] = $profile[$key] }
}
if ($PrepareOnly) {
    [pscustomobject]@{ executable = $exe; arguments = $arguments; environment = $environment } | ConvertTo-Json -Depth 3
    exit 0
}
if (-not (Test-Path -LiteralPath $exe)) { throw "Extract the entire release ZIP; executable missing: $exe" }
$saved = @{}
try {
    foreach ($key in $environment.Keys) {
        $saved[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $environment[$key], 'Process')
    }
    $process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -Wait -PassThru
    $code = $process.ExitCode
} finally {
    foreach ($key in $saved.Keys) { [Environment]::SetEnvironmentVariable($key, $saved[$key], 'Process') }
}
exit $code
