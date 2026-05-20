# Validador V8B2 - Wrapper PowerShell
# Uso:
#   .\validate_returned_logs.ps1 -GoldenLog logs/golden.txt -ExtendedLog logs/extended.txt -AnomalyLog logs/anomaly.txt
#   .\validate_returned_logs.ps1 -GoldenLog logs/golden.txt -OutputJson out.json

param(
    [string]$GoldenLog,
    [string]$ExtendedLog,
    [string]$AnomalyLog,
    [string]$OutputJson,
    [string]$OutputCsv
)

# Verifica se nenhum log foi fornecido
if (-not $GoldenLog -and -not $ExtendedLog -and -not $AnomalyLog) {
    Write-Host "Uso: .\validate_returned_logs.ps1 -GoldenLog <path> [-ExtendedLog <path>] [-AnomalyLog <path>] [-OutputJson <path>] [-OutputCsv <path>]"
    exit 1
}

# Constrói comando Python
$pythonArgs = @("scripts/validate_returned_logs.py")

if ($GoldenLog) { $pythonArgs += "--golden"; $pythonArgs += $GoldenLog }
if ($ExtendedLog) { $pythonArgs += "--extended"; $pythonArgs += $ExtendedLog }
if ($AnomalyLog) { $pythonArgs += "--anomaly"; $pythonArgs += $AnomalyLog }
if ($OutputJson) { $pythonArgs += "--json"; $pythonArgs += $OutputJson }
if ($OutputCsv) { $pythonArgs += "--csv"; $pythonArgs += $OutputCsv }

# Executa Python
Write-Host "Executando validação V8B2..." -ForegroundColor Cyan
Write-Host "Command: python $($pythonArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

python @pythonArgs
$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "Validação bem-sucedida!" -ForegroundColor Green
} else {
    Write-Host "Validação falhou; veja mensagens acima." -ForegroundColor Red
}

exit $exitCode
