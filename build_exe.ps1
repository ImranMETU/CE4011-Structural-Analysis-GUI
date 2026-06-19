$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SpecFile = Join-Path $ProjectRoot "CE4011_Solver.spec"
$Python = (Get-Command python -ErrorAction Stop).Source
$EnvironmentRoot = Split-Path -Parent $Python

# Conda activation normally supplies these paths. Adding them explicitly makes
# Tcl/Tk, OpenSSL, compression, and FFI DLL collection deterministic.
$env:PATH = @(
    $EnvironmentRoot
    (Join-Path $EnvironmentRoot "Library\bin")
    (Join-Path $EnvironmentRoot "DLLs")
    (Join-Path $EnvironmentRoot "Scripts")
    $env:PATH
) -join ";"

Push-Location $ProjectRoot
try {
    & $Python -m PyInstaller --clean --noconfirm $SpecFile
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    $DistFolder = Join-Path $ProjectRoot "dist\CE4011_Solver"
    $Executable = Join-Path $DistFolder "CE4011_Solver.exe"
    $InstallerReadme = Join-Path $ProjectRoot "INSTALLER_README.txt"

    if (-not (Test-Path -LiteralPath $Executable)) {
        throw "Expected executable was not created: $Executable"
    }

    # Keep the usage warning visible beside the executable as well as bundled
    # in _internal for completeness.
    Copy-Item -LiteralPath $InstallerReadme -Destination $DistFolder -Force

    Write-Host ""
    Write-Host "CE4011 onedir build completed successfully."
    Write-Host "Run only from:"
    Write-Host $Executable
    Write-Host ""
    Write-Host "Distribute the complete folder:"
    Write-Host $DistFolder
}
finally {
    Pop-Location
}
