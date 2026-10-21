# Sobe o ambiente de desenvolvimento completo: WhatsApp (Evolution no Docker), sistema (Django) e site (Vite).
# Uso: .\iniciar.ps1   (ou dois cliques em iniciar.cmd)
# Cada servidor abre na sua própria janela; feche a janela (ou Ctrl+C nela) para parar aquele servidor.
$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$python = Join-Path $raiz ".venv\Scripts\python.exe"

function Porta-EmUso([int]$porta) {
    [bool](Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue)
}

# IP do computador na rede (o da interface com acesso à internet), para abrir pelo celular
$ip = (Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" } |
       Select-Object -First 1).IPv4Address.IPAddress
if (-not $ip) { $ip = "localhost" }

Write-Host ""
Write-Host "Don Corleone - iniciando o ambiente" -ForegroundColor Yellow

# 1. WhatsApp (Evolution API)
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "[1/3] WhatsApp (Evolution no Docker)..."
    Push-Location $raiz
    # docker compose escreve o progresso no stderr: o resultado vem do código de saída
    $ErrorActionPreference = "Continue"
    docker compose up -d 2>$null | Out-Null
    $dockerOk = $LASTEXITCODE -eq 0
    $ErrorActionPreference = "Stop"
    Pop-Location
    if ($dockerOk) { Write-Host "      ok" -ForegroundColor Green }
    else { Write-Host "      Docker não respondeu (o Docker Desktop está aberto?). Seguindo sem o WhatsApp." -ForegroundColor DarkYellow }
} else {
    Write-Host "[1/3] Docker não instalado: seguindo sem o WhatsApp." -ForegroundColor DarkYellow
}

# 2. Sistema (Django)
if (Porta-EmUso 8000) {
    Write-Host "[2/3] Sistema já está rodando na porta 8000." -ForegroundColor Green
} else {
    Write-Host "[2/3] Sistema (Django) abrindo em nova janela..."
    Start-Process powershell -WorkingDirectory $raiz -ArgumentList @(
        "-NoExit", "-Command",
        "`$Host.UI.RawUI.WindowTitle = 'Don Corleone - Sistema (Django)'; & '$python' backend\manage.py runserver 0.0.0.0:8000"
    )
}

# 3. Site (Vite), apontando a API para o IP da rede para funcionar também no celular
if (Porta-EmUso 3000) {
    Write-Host "[3/3] Site já está rodando na porta 3000." -ForegroundColor Green
} else {
    Write-Host "[3/3] Site (Vite) abrindo em nova janela..."
    Start-Process powershell -WorkingDirectory $raiz -ArgumentList @(
        "-NoExit", "-Command",
        "`$Host.UI.RawUI.WindowTitle = 'Don Corleone - Site (Vite)'; `$env:VITE_API_URL = 'http://${ip}:8000/api/v1'; npm run dev -- --host"
    )
}

Write-Host ""
Write-Host "Pronto. Endereços:" -ForegroundColor Yellow
Write-Host "  Site .......... http://localhost:3000   (celular: http://${ip}:3000)"
Write-Host "  Painel ........ http://localhost:8000/painel/   (celular: http://${ip}:8000/painel/)"
Write-Host "  Para gerar links e QR Codes dos entregadores, abra o painel pelo endereço do celular."
Write-Host ""
