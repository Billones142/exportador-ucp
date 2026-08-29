#Requires -Version 5.1
<#
Instalador de un comando para "Exportador UCP" (plugin de QGIS).

Uso (PowerShell, no cmd.exe):
    irm https://raw.githubusercontent.com/Billones142/exportador-ucp/main/install.ps1 | iex

Variables de entorno opcionales (definirlas ANTES de correr el comando de arriba):
    $env:EXPORTADOR_UCP_PROFILE      Nombre del perfil de QGIS a usar (por defecto "default").
    $env:EXPORTADOR_UCP_PLUGINS_DIR  Ruta exacta a la carpeta "python/plugins" a usar,
                                      para saltarse la deteccion automatica (util con
                                      instalaciones portables de QGIS).
#>

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "OK  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "!!  $msg" -ForegroundColor Yellow }

try {
    [Net.ServicePointManager]::SecurityProtocol = `
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch {
    # TLS 1.2 ya viene habilitado por defecto en versiones recientes de PowerShell.
}

$RepoZipUrl  = "https://github.com/Billones142/exportador-ucp/archive/refs/heads/main.zip"
$PluginName  = "exportador_ucp_plugin"
$ProfileName = if ($env:EXPORTADOR_UCP_PROFILE) { $env:EXPORTADOR_UCP_PROFILE } else { "default" }

Write-Step "Buscando la carpeta de plugins de QGIS..."

function Find-QgisPluginsDir {
    param([string]$ProfileName)

    if ($env:EXPORTADOR_UCP_PLUGINS_DIR) {
        return $env:EXPORTADOR_UCP_PLUGINS_DIR
    }

    $qgisRoot = Join-Path $env:APPDATA "QGIS"
    if (-not (Test-Path $qgisRoot)) {
        return $null
    }

    $candidates = Get-ChildItem -Path $qgisRoot -Directory -Filter "QGIS*" -ErrorAction SilentlyContinue |
        Sort-Object {
            $versionMatch = [regex]::Match($_.Name, '\d+')
            if ($versionMatch.Success) { [int]$versionMatch.Value } else { 0 }
        } -Descending

    foreach ($candidate in $candidates) {
        $pluginsDir = Join-Path $candidate.FullName "profiles\$ProfileName\python\plugins"
        if (Test-Path (Join-Path $candidate.FullName "profiles\$ProfileName")) {
            return $pluginsDir
        }
    }

    return $null
}

$pluginsDir = Find-QgisPluginsDir -ProfileName $ProfileName

if (-not $pluginsDir) {
    Write-Warn "No se encontro el perfil '$ProfileName' de QGIS en $env:APPDATA\QGIS."
    Write-Warn "Instala/abri QGIS al menos una vez para que cree su perfil, o define"
    Write-Warn '  $env:EXPORTADOR_UCP_PLUGINS_DIR = "C:\ruta\a\python\plugins"'
    Write-Warn "antes de correr este instalador."
    exit 1
}

Write-Ok "Carpeta de plugins: $pluginsDir"

New-Item -ItemType Directory -Force -Path $pluginsDir | Out-Null

$tempBase = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
$tempRoot = Join-Path $tempBase ("exportador-ucp-" + [guid]::NewGuid().ToString("N"))
$zipPath  = Join-Path $tempRoot "exportador-ucp.zip"
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

try {
    Write-Step "Descargando exportador-ucp desde GitHub..."
    Invoke-WebRequest -Uri $RepoZipUrl -OutFile $zipPath -UseBasicParsing
    Write-Ok "Descarga completa."

    Write-Step "Extrayendo..."
    Expand-Archive -Path $zipPath -DestinationPath $tempRoot -Force

    $extractedPluginDir = Get-ChildItem -Path $tempRoot -Directory -Filter "exportador-ucp-*" |
        Select-Object -First 1 |
        ForEach-Object { Join-Path $_.FullName $PluginName }

    if (-not $extractedPluginDir -or -not (Test-Path $extractedPluginDir)) {
        throw "No se encontro la carpeta '$PluginName' dentro del archivo descargado."
    }

    $targetDir = Join-Path $pluginsDir $PluginName
    if (Test-Path $targetDir) {
        Write-Step "Reemplazando instalacion anterior en $targetDir ..."
        Remove-Item -Path $targetDir -Recurse -Force
    }

    Write-Step "Copiando el plugin a $targetDir ..."
    Copy-Item -Path $extractedPluginDir -Destination $targetDir -Recurse -Force
    Write-Ok "Plugin copiado."
} finally {
    Remove-Item -Path $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Ok "Exportador UCP instalado en: $targetDir"
Write-Host "Proximos pasos:" -ForegroundColor Cyan
Write-Host "  1. Cerra QGIS si estaba abierto y volve a abrirlo."
Write-Host "  2. Anda a Complementos > Administrar/Instalar complementos > solapa Instalados."
Write-Host "  3. Activa 'Exportador UCP'."
