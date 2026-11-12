<#
.SYNOPSIS
    Reproduce en local los tres jobs del CI (lint, tests con PostgreSQL, build de la imagen).

.DESCRIPTION
    Por defecto verifica el working copy. Con -Clon clona HEAD a una carpeta temporal y corre ahí:
    así se ve exactamente lo versionado, que es lo único que ve el runner del CI.
    Usa un venv nuevo con Python 3.13 (el mismo del workflow) y una base PostgreSQL de prueba
    levantada con `docker compose -p agenda-citas-test` en el puerto 5434. Esa base, la imagen
    de prueba y el venv SIEMPRE se eliminan al terminar (bloque finally), aunque algo falle.

.EXAMPLE
    .\scripts\verificar.ps1          # working copy
    .\scripts\verificar.ps1 -Clon    # clon limpio de HEAD
#>
param([switch]$Clon)

$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent $PSScriptRoot
$trabajo = $raiz
$temporal = Join-Path $env:TEMP ("agenda-verificar-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$proyecto = "agenda-citas-test"
$puertoBd = 5434
$fallos = 0

function Ejecutar([string]$descripcion, [scriptblock]$comando) {
    Write-Host "== $descripcion" -ForegroundColor Cyan
    & $comando
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   FALLO: $descripcion" -ForegroundColor Red
        $script:fallos++
        return $false
    }
    Write-Host "   ok" -ForegroundColor Green
    return $true
}

try {
    New-Item -ItemType Directory -Path $temporal | Out-Null
    if ($Clon) {
        $trabajo = Join-Path $temporal "clon"
        Write-Host "== Clonando HEAD a $trabajo" -ForegroundColor Cyan
        git clone --quiet $raiz $trabajo
        if ($LASTEXITCODE -ne 0) { throw "No se pudo clonar HEAD (¿hay commits?)." }
    }
    Set-Location $trabajo

    # venv nuevo en la carpeta temporal: nada de lo instalado "de rebote" cuenta.
    $venv = Join-Path $temporal "venv"
    Ejecutar "venv con Python 3.13" { py -3.13 -m venv $venv } | Out-Null
    $py = Join-Path $venv "Scripts\python.exe"
    Ejecutar "instalar dependencias (pip install -e .[dev])" { & $py -m pip install -q -e ".[dev]" } | Out-Null

    # --- job 1: lint -----------------------------------------------------------------
    Ejecutar "ruff check" { & $py -m ruff check . } | Out-Null
    Ejecutar "ruff format --check" { & $py -m ruff format --check . } | Out-Null

    # --- job 2: pruebas contra PostgreSQL real ---------------------------------------
    # Las variables del proceso ganan sobre el .env, y se limpian en el finally.
    $env:POSTGRES_PASSWORD = "verificar"
    $env:DB_PUERTO_HOST = "$puertoBd"
    $env:DATABASE_URL = "postgresql://agenda:verificar@localhost:$puertoBd/agenda"
    $baseLista = Ejecutar "PostgreSQL de prueba ($proyecto, puerto $puertoBd)" {
        docker compose -p $proyecto up -d --wait db
    }
    if ($baseLista) {
        New-Item -ItemType Directory -Force -Path evidencias | Out-Null
        Ejecutar "pytest con cobertura >= 85 % y evidencia JUnit" {
            & $py -m pytest -rs --cov --cov-report=term-missing --cov-fail-under=85 `
                --junitxml=evidencias/junit-pruebas.xml | Tee-Object -FilePath evidencias/salida-pytest.txt
            # Tee-Object es un cmdlet: $LASTEXITCODE sigue siendo el de pytest.
        } | Out-Null
    }

    # --- job 3: build y arranque de la imagen ----------------------------------------
    $imagen = "agenda-citas:verificar"
    $construida = Ejecutar "docker build" { docker build -q -t $imagen . }
    if ($construida) {
        docker run -d --name agenda-verificar -p 18001:8001 -e ALMACENAMIENTO=memoria $imagen | Out-Null
        $vivo = $false
        foreach ($i in 1..30) {
            try {
                $r = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:18001/livez" -TimeoutSec 2
                if ($r.StatusCode -eq 200) { $vivo = $true; break }
            } catch { Start-Sleep -Seconds 1 }
        }
        if ($vivo) { Write-Host "== La imagen arranca: /livez responde`n   ok" -ForegroundColor Green }
        else { Write-Host "   FALLO: /livez no respondió" -ForegroundColor Red; docker logs agenda-verificar; $fallos++ }
    }
}
finally {
    Write-Host "== Limpieza (la base de prueba, la imagen y el venv siempre se eliminan)" -ForegroundColor Cyan
    Set-Location $raiz
    docker rm -f agenda-verificar 2>$null | Out-Null
    docker compose -p $proyecto down -v --remove-orphans
    docker rmi agenda-citas:verificar 2>$null | Out-Null
    Remove-Item Env:POSTGRES_PASSWORD, Env:DB_PUERTO_HOST, Env:DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $temporal -ErrorAction SilentlyContinue
}

if ($fallos -eq 0) { Write-Host "Todo en verde." -ForegroundColor Green; exit 0 }
Write-Host "$fallos verificación(es) fallaron. No pushees todavía." -ForegroundColor Red
exit 1
