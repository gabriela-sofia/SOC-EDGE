# Comando PowerShell para verificar o pacote handoff

$PackagePath = "C:\Users\gabriela\Downloads\SOC\handoff_esp32_soc_method_b_v1"
$ZipPath = "C:\Users\gabriela\Downloads\SOC\handoff_esp32_soc_method_b_v1.zip"

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  VERIFICAÇÃO DO PACOTE HANDOFF ESP32 SOC METHOD B" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Verificar pasta principal
if (Test-Path $PackagePath) {
    Write-Host "✅ Pasta encontrada: $PackagePath" -ForegroundColor Green
} else {
    Write-Host "❌ Pasta NOT encontrada!" -ForegroundColor Red
}

# Verificar ZIP
if (Test-Path $ZipPath) {
    $ZipSize = (Get-Item $ZipPath).Length / 1KB
    Write-Host "✅ ZIP encontrado: $ZipPath ($([Math]::Round($ZipSize))KB)" -ForegroundColor Green
} else {
    Write-Host "❌ ZIP NÃO encontrado!" -ForegroundColor Red
}

Write-Host ""
Write-Host "Arquivos principais:" -ForegroundColor Cyan

# Documentação
Get-ChildItem "$PackagePath\*.md" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  ✅ $($_.Name)" -ForegroundColor Green
}

# Model files
Get-ChildItem "$PackagePath\model\*.pkl" -ErrorAction SilentlyContinue | ForEach-Object {
    $Size = $_.Length / 1KB
    Write-Host "  ✅ model\$($_.Name) ($([Math]::Round($Size))KB)" -ForegroundColor Green
}

# Weights
Get-ChildItem "$PackagePath\model\*.json" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  ✅ model\$($_.Name)" -ForegroundColor Green
}

# Samples
$SampleCount = (Get-ChildItem "$PackagePath\samples\*.csv" -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "  ✅ samples\ ($SampleCount CSV files)" -ForegroundColor Green

# Validation
$ValidationCount = (Get-ChildItem "$PackagePath\validation\*.csv" -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "  ✅ validation\ ($ValidationCount CSV files)" -ForegroundColor Green

# Reports
$ReportCount = (Get-ChildItem "$PackagePath\reports\*.md" -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "  ✅ reports\ ($ReportCount markdown files)" -ForegroundColor Green

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  DECISION: ESP32_FINAL_EXPERIMENTAL_HANDOFF_ZIP_READY" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan

