<#
.SYNOPSIS
  Push del estado actual a origin/main para forzar redeploy en Streamlit Cloud.

.DESCRIPTION
  1. Verifica que estamos dentro del repo de Engordando-Holando.
  2. Muestra el git status.
  3. (Salvo -Force) pide confirmación.
  4. Agrega TODO, commitea con el mensaje pasado, pushea a la branch actual.
  5. Recuerda la URL pública y el atajo Ctrl+F5 para bypass de cache del navegador.

  Streamlit Cloud detecta el push a main y redeploya solo en ~1-2 min. La
  versión visible en el sidebar (commit hash + fecha) confirma que el deploy
  pasó: si después de 2 minutos seguís viendo el hash anterior, hacé Ctrl+F5.

.PARAMETER Message
  Mensaje de commit. Obligatorio. Si tiene espacios, ponelo entre comillas.

.PARAMETER Force
  Saltea la confirmación interactiva. Útil para scripts encadenados.

.EXAMPLE
  .\scripts\deploy.ps1 "Fix grafico de sensibilidad"

.EXAMPLE
  .\scripts\deploy.ps1 -Message "Update params" -Force
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Message,

    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Verificar que estamos dentro de un repo git
try {
    $repoRoot = & git rev-parse --show-toplevel
} catch {
    Write-Host "ERROR: no estas dentro de un repo git." -ForegroundColor Red
    exit 1
}

Set-Location $repoRoot
$branch = & git rev-parse --abbrev-ref HEAD

# Mostrar lo que se va a commitear
Write-Host ""
Write-Host "Repo:   $repoRoot" -ForegroundColor DarkGray
Write-Host "Branch: $branch" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Cambios a commitear:" -ForegroundColor Cyan
& git status --short
Write-Host ""

# Confirmación
if (-not $Force) {
    $confirm = Read-Host "Commit y push a origin/$branch con mensaje '$Message'? [y/N]"
    if ($confirm -notmatch '^[Yy]') {
        Write-Host "Abortado." -ForegroundColor Yellow
        exit 0
    }
}

# Stage + commit + push
& git add -A
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Si no hay nada staged, evitar el commit vacio
$staged = & git diff --cached --name-only
if (-not $staged) {
    Write-Host "No hay cambios staged. Nada que commitear." -ForegroundColor Yellow
    exit 0
}

& git commit -m $Message
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& git push origin $branch
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: push fallo. Tu commit local quedo hecho." -ForegroundColor Red
    Write-Host "Resolvelo (ej: git pull --rebase) y volve a correr este script." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Push OK. Streamlit Cloud redeploya en ~1-2 min." -ForegroundColor Green
Write-Host "URL: https://engordando-holando.streamlit.app/" -ForegroundColor Green
Write-Host ""
Write-Host "Tip: si seguis viendo la version vieja despues de 2 min," -ForegroundColor DarkGray
Write-Host "hace Ctrl+F5 en el navegador (bypass de cache)." -ForegroundColor DarkGray
