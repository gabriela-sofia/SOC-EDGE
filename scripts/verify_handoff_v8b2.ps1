Param(
    [string]$PackagePath = "embedded/handoff_v8b2"
)

$ErrorActionPreference = "Stop"

$requiredDirs = @(
    "firmware",
    "include",
    "replay",
    "anomaly",
    "validation",
    "manifests"
)

$requiredFiles = @(
    "firmware/firmware_soc_v8b2_canonical.ino",
    "include/canonical_model_weights_v8b2.h",
    "include/replay_vectors_v8b2.h",
    "replay/canonical_golden_vectors_v8b2.csv",
    "replay/canonical_extended_replay_v8b2.csv",
    "replay/canonical_extended_reference_v8b2.csv",
    "anomaly/anomaly_replay_scenarios_v8b2.csv",
    "anomaly/anomaly_expected_flags_v8b2.csv",
    "validation/validate_esp32_v8b2.py",
    "manifests/canonical_replay_manifest_v8b2.csv",
    "manifests/MODEL_MANIFEST_V8B2.md"
)

Write-Host "Verificando pacote publico V8B2: $PackagePath"

if (-not (Test-Path -LiteralPath $PackagePath -PathType Container)) {
    Write-Error "Pacote nao encontrado: $PackagePath"
}

$missing = New-Object System.Collections.Generic.List[string]

foreach ($dir in $requiredDirs) {
    $path = Join-Path $PackagePath $dir
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        $missing.Add($dir)
    }
}

foreach ($file in $requiredFiles) {
    $path = Join-Path $PackagePath $file
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $missing.Add($file)
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Itens ausentes:" -ForegroundColor Red
    foreach ($item in $missing) {
        Write-Host "  - $item" -ForegroundColor Red
    }
    exit 1
}

Write-Host "Pacote V8B2 completo para verificacao estrutural." -ForegroundColor Green
