[CmdletBinding()]
param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$desktopRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $desktopRoot
$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

Push-Location $projectRoot
try {
    & $python -m pip install -r (Join-Path $desktopRoot "requirements-build.txt")
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias de compilación." }

    $arguments = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", "HACKAJAL",
        "--windowed",
        "--onedir",
        "--paths", $desktopRoot,
        "--add-data", "$desktopRoot\\resources;resources",
        "--collect-all", "folium",
        "--collect-all", "branca",
        "--collect-submodules", "PySide6.QtWebEngineCore",
        "--collect-submodules", "PySide6.QtWebEngineWidgets",
        "--distpath", (Join-Path $projectRoot "dist\\desktop"),
        "--workpath", (Join-Path $projectRoot "build\\desktop"),
        "--specpath", (Join-Path $projectRoot "build\\desktop"),
        (Join-Path $desktopRoot "main.py")
    )

    if ($Clean) {
        foreach ($target in @(
            (Join-Path $projectRoot "dist\\desktop\\HACKAJAL"),
            (Join-Path $projectRoot "build\\desktop")
        )) {
            if (Test-Path -LiteralPath $target) {
                Remove-Item -LiteralPath $target -Recurse -Force
            }
        }
    }

    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw "Falló el empaquetado de HACKAJAL." }

    $targetDist = Join-Path $projectRoot "dist\\desktop\\HACKAJAL"
    $destResources = Join-Path $targetDist "resources"
    if (-not (Test-Path -LiteralPath $destResources)) {
        Copy-Item -Path (Join-Path $desktopRoot "resources") -Destination $destResources -Recurse -Force
    }
    $exampleEnv = Join-Path $desktopRoot ".env.example"
    if (Test-Path -LiteralPath $exampleEnv) {
        Copy-Item -Path $exampleEnv -Destination (Join-Path $targetDist ".env.example") -Force
    }

    Write-Host "Ejecutable generado en: dist\\desktop\\HACKAJAL\\HACKAJAL.exe"
}
finally {
    Pop-Location
}
