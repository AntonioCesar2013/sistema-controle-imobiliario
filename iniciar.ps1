$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$candidatos = @(
    "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
)
$python = $candidatos | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $python) {
    $comando = Get-Command python -ErrorAction SilentlyContinue
    if ($comando -and $comando.Source -notmatch "WindowsApps") { $python = $comando.Source }
}
if (-not $python) {
    Write-Host "Python 3 não foi encontrado. Instale-o e tente novamente." -ForegroundColor Red
    Read-Host "Pressione ENTER para fechar"
    exit 1
}

try {
    & $python -c "import webview" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Instalando o componente de interface WebView2..." -ForegroundColor Yellow
        & $python -m pip install -r requirements.txt
    }
    & $python main.py
}
catch {
    Write-Host $_ -ForegroundColor Red
    Read-Host "Pressione ENTER para fechar"
    exit 1
}

