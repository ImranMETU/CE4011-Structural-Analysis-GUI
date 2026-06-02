param(
    [string]$CourseRoot = "c:\DDrive\Imran\METU\Coursework\CE4011"
)

$ErrorActionPreference = "Stop"

$A3 = Join-Path $CourseRoot "Assignment3"
$A4 = Join-Path $CourseRoot "Assignment4"

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Safe-Copy([string]$Source, [string]$Dest) {
    if (-not (Test-Path -LiteralPath $Source)) {
        Write-Host "MISSING SOURCE: $Source"
        return
    }

    $destDir = Split-Path -Path $Dest -Parent
    Ensure-Dir $destDir

    if (-not (Test-Path -LiteralPath $Dest)) {
        Copy-Item -LiteralPath $Source -Destination $Dest
        Write-Host "COPIED: $Source -> $Dest"
        return
    }

    $srcHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Source).Hash
    $dstHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Dest).Hash

    if ($srcHash -eq $dstHash) {
        Write-Host "SKIP SAME: $Dest"
    }
    else {
        $incoming = "$Dest.incoming"
        Copy-Item -LiteralPath $Source -Destination $incoming -Force
        Write-Host "DIFF EXISTS, wrote incoming copy: $incoming"
    }
}

# Target directories
$dirs = @(
    "$A4\src\model",
    "$A4\src\matrixlib",
    "$A4\src\io",
    "$A4\src\thermal",
    "$A4\tests\unit",
    "$A4\tests\interface",
    "$A4\tests\regression",
    "$A4\inputs\q2\xml",
    "$A4\inputs\regression\xml",
    "$A4\inputs\json",
    "$A4\results\solver",
    "$A4\results\benchmark\ftool",
    "$A4\results\benchmark\sap2000",
    "$A4\report\chapters",
    "$A4\report\images",
    "$A4\report\tables",
    "$A4\docs"
)
$dirs | ForEach-Object { Ensure-Dir $_ }

# Copy solver sources touched for Assignment 4
Get-ChildItem -LiteralPath "$A3\q2_frame_analysis\model" -File -Filter *.py | ForEach-Object {
    Safe-Copy $_.FullName (Join-Path "$A4\src\model" $_.Name)
}
Safe-Copy "$A3\q2_frame_analysis\matrixlib\__init__.py" "$A4\src\matrixlib\__init__.py"

# Copy Assignment4 source utilities
Safe-Copy "$A4\xml_loader.py" "$A4\src\io\xml_loader.py"
Safe-Copy "$A4\thermal\thermal_load.py" "$A4\src\thermal\thermal_load.py"
Safe-Copy "$A4\thermal\__init__.py" "$A4\src\thermal\__init__.py"

# Split tests by category (copy-only)
Safe-Copy "$A4\tests\test_thermal_bar.py" "$A4\tests\unit\test_thermal_bar.py"
Safe-Copy "$A4\tests\test_thermal_beam_gradient.py" "$A4\tests\unit\test_thermal_beam_gradient.py"
Safe-Copy "$A4\tests\test_thermal_combined.py" "$A4\tests\interface\test_thermal_combined.py"
Safe-Copy "$A4\tests\test_xml_regression.py" "$A4\tests\regression\test_xml_regression.py"

# Inputs
Safe-Copy "$A4\ModelA.xml" "$A4\inputs\q2\xml\ModelA.xml"
Safe-Copy "$A4\ModelB.xml" "$A4\inputs\q2\xml\ModelB.xml"
Get-ChildItem -LiteralPath "$A4\inputs\regression" -File -Filter *.xml | ForEach-Object {
    Safe-Copy $_.FullName (Join-Path "$A4\inputs\regression\xml" $_.Name)
}
Get-ChildItem -LiteralPath "$A4\inputs" -File -Filter *.json | ForEach-Object {
    Safe-Copy $_.FullName (Join-Path "$A4\inputs\json" $_.Name)
}

# Results / generated outputs
$resultFiles = @(
    "ModelA_RESULTS.txt",
    "Model_B_Results.txt",
    "REGRESSION_TEST_RESULTS.txt",
    "TEST_RESULTS.txt",
    "FINAL_TEST_RESULTS.txt",
    "VALIDATION_REPORT.txt",
    "IMPLEMENTATION_SUMMARY.txt"
)
foreach ($name in $resultFiles) {
    Safe-Copy (Join-Path $A4 $name) (Join-Path "$A4\results\solver" $name)
}

# Benchmark artifacts
$benchmarkFiles = @(
    "ModelA_Ftool.png",
    "ModelB_Ftool.png",
    "Regression_Thermal_Uniform.png",
    "Regression_Thermal_Gradient.png",
    "Regression_Thermal_Combined.png",
    "Regression_Settlement.png",
    "test_results_screenshot.png"
)
foreach ($name in $benchmarkFiles) {
    Safe-Copy (Join-Path $A4 $name) (Join-Path "$A4\results\benchmark\ftool" $name)
}

# Report assets (copy only, keep originals as canonical build root)
$chapters = @(
    "main.tex",
    "Chapter1_Assignment4_ProgramDesign.tex",
    "Chapter2_Assignment4_TestingVerification.tex",
    "Chapter3_Assignment4_StructuralAnalysisCases.tex",
    "Chapter4_Assignment4_Conclusion.tex",
    "Chapter5_Assignment4_References.tex",
    "bibliography.bib"
)
foreach ($name in $chapters) {
    Safe-Copy (Join-Path $A4 $name) (Join-Path "$A4\report\chapters" $name)
}

$imageFiles = @(
    "UML_4.png",
    "ActivityDiagram.png",
    "ModelA.png",
    "ModelB.png"
)
foreach ($name in $imageFiles) {
    Safe-Copy (Join-Path $A4 $name) (Join-Path "$A4\report\images" $name)
}

Write-Host "Migration pass completed."
