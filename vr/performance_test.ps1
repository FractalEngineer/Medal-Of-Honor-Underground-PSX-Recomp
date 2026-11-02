# Explicit operator playtest route. Personal saves and the production runtime
# are never destinations. Repeated preparation preserves progress in this copy.
function Get-PerformanceFileHash {
    param([string]$Path)
    $stream = [IO.File]::OpenRead($Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose(); $stream.Dispose() }
}

function Initialize-PerformancePlaytest {
    param([Parameter(Mandatory=$true)][string]$RepositoryRoot)

    $candidate = Join-Path $RepositoryRoot 'analysis\builds\preflight-enhanced'
    $exe = Join-Path $candidate 'Medal_of_Honor_Underground_Recompiled.exe'
    $manifestPath = Join-Path $candidate 'Medal_of_Honor_Underground_Recompiled.execution.json'
    $evidencePath = Join-Path $RepositoryRoot 'vr\proof\render-kernel-checkpoint-receipt.json'
    $evidence = Get-Content -LiteralPath $evidencePath -Raw | ConvertFrom-Json
    $tested = $evidence.final_rebuilt_enhanced_control
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.profile -ne 'ENHANCED' -or
        $manifest.identity -ne $tested.execution_identity -or
        (Get-PerformanceFileHash -Path $exe) -ne $tested.binary_sha256) {
        throw 'Performance build differs from its tested artifact. Requalify it before preparing a playtest.'
    }
    $cache = Get-Content -LiteralPath (Join-Path $candidate 'CMakeCache.txt') -Raw
    $required = @{
        CMAKE_BUILD_TYPE = 'Release'; PSX_DEBUG_TOOLS = 'OFF'; PSX_OPENXR = 'ON'
        PSX_RUNTIME_IPO = 'OFF'; MOHU_VR_NATIVE_PROFILE = 'OFF'
        MOHU_VR_PREFLIGHT_HARNESS = 'OFF'; MOHU_VR_PACKET_HARNESS = 'OFF'
        MOHU_VR_HOST_PREFLIGHT = 'ON'; MOHU_VR_HOST_PACKET = 'ON'
    }
    foreach ($key in $required.Keys) {
        if ($cache -notmatch ('(?m)^' + $key + ':[^=]+=' + $required[$key] + '\r?$')) {
            throw "Performance build needs $key=$($required[$key])."
        }
    }
    $testRoot = Join-Path $RepositoryRoot 'analysis\playtest\render-kernels'
    $saves = Join-Path $testRoot 'saves'
    $bindingPath = Join-Path $testRoot 'profile.json'
    if (Test-Path -LiteralPath $bindingPath) {
        $binding = Get-Content -LiteralPath $bindingPath -Raw | ConvertFrom-Json
        if ($binding.execution_identity -ne $manifest.identity) {
            throw 'Existing performance playtest saves belong to another execution identity; preserve them.'
        }
    } elseif ((Test-Path -LiteralPath $saves) -and
              (Get-ChildItem -LiteralPath $saves -Recurse -File | Select-Object -First 1)) {
        throw 'Existing performance saves have no profile binding; refusing to overwrite or adopt them.'
    }
    New-Item -ItemType Directory -Path (Join-Path $saves 'openbios') -Force | Out-Null
    $copied = @()
    foreach ($name in @('card1.mcd', 'card2.mcd')) {
        $source = Join-Path (Join-Path $RepositoryRoot 'saves') $name
        $destination = Join-Path $saves $name
        if ((Test-Path -LiteralPath $source) -and -not (Test-Path -LiteralPath $destination)) {
            Copy-Item -LiteralPath $source -Destination $destination
            $copied += $destination
        }
    }
    if (-not (Test-Path -LiteralPath $bindingPath)) {
        [pscustomobject]@{
            execution_identity = $manifest.identity
            initial_binary_sha256 = $tested.binary_sha256
            copied_files = $copied
            personal_save_destination = $false
        } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $bindingPath -Encoding UTF8
    }
    [pscustomobject]@{
        build_directory = 'analysis\builds\preflight-enhanced'
        game_config = Join-Path $candidate 'game.toml'
        memcard_directory = $saves
        execution_identity = $manifest.identity
        disc = Join-Path $RepositoryRoot 'Medal of Honor - Underground\Medal of Honor - Underground (USA).cue'
    }
}
