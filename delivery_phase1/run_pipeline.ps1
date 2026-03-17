$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = "c:/Users/ASUS/Downloads/ThinkX_database/.venv/Scripts/python.exe"

Write-Host "[1/5] merge telemetry"
& $Py "$Root/scripts/01_merge_telemetry.py"
Write-Host "[2/5] aggregate daily"
& $Py "$Root/scripts/02_aggregate_daily.py"
Write-Host "[3/5] build facility features"
& $Py "$Root/scripts/03_build_facility_features.py"
Write-Host "[4/5] build model panel"
& $Py "$Root/scripts/04_build_model_panel.py"
Write-Host "[5/5] generate labels"
& $Py "$Root/scripts/05_generate_labels.py"
Write-Host "[6/6] train models and generate multi-risk outputs"
& $Py "$Root/scripts/06_train_models.py"
Write-Host "Pipeline finished. Outputs in delivery_phase1/data/processed, delivery_phase1/output, and delivery_phase1/reports"
