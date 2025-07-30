# ==============================================================================
# PowerShell Script to run a batch of Sugarscape experiments
# ==============================================================================
#
# Description:
# This script executes a series of `run_batch.py` commands in sequence.
# It manually times each command to allow for real-time console output
# from the python script, which is buffered by PowerShell's Measure-Command.
# It reports individual and total runtimes in hh:mm:ss format.
#
# How to Run:
# 1. Open a PowerShell terminal.
# 2. Navigate to the `.../mesa/examples/advanced/` directory.
# 3. Run the script by typing: .\sugarscape_g1mt\run_experiments.ps1
#
# ==============================================================================

# --- Set Correct Working Directory ---
$scriptDir = $PSScriptRoot
$projectRoot = (Get-Item -Path $scriptDir).Parent.FullName
Set-Location -Path $projectRoot
Write-Host "Working directory set to: $projectRoot" -ForegroundColor Gray


# Start a timer for the total batch runtime
$total_start_time = Get-Date
Clear-Host
Write-Host ">>> Starting full experiment batch at $total_start_time" -ForegroundColor Green
Write-Host "-------------------------------------------------------------"

# --- Experiment 1: Baseline (No Investments, No Lending) ---
Write-Host "`n[1/4] Running: Baseline Experiment..." -ForegroundColor Cyan
$run1_start = Get-Date

python -m sugarscape_g1mt.run_batch --run_group "baseline" `
    --total_steps 500 `
    --replications 1 `
    --initial_population "[100,200,300,400]" `
    --agent_re_spawn true `
    --metabolism "[3.1, 3.1]" `
    --vision "[1, 1]" `
    --endowment "[5, 5]" `
    --log_agent_data true `
    --age "[1000,1000]" `
    --investments_enabled false `
    --lending_enabled false `
    --deposits_enabled false `
    --tag prod *>&1

$run1_duration = (Get-Date) - $run1_start
Write-Host ("`n`t- Baseline run finished in {0}" -f $run1_duration.ToString('hh\:mm\:ss')) -ForegroundColor Yellow
Write-Host "-------------------------------------------------------------"


# --- Experiment 2: Investments Enabled (No Lending) ---
Write-Host "`n[2/4] Running: Investments-Enabled Experiment..." -ForegroundColor Cyan
$run2_start = Get-Date

python -m sugarscape_g1mt.run_batch --run_group "baseline_investments" `
    --total_steps 500 `
    --replications 1 `
    --initial_population "[100,200,300,400]" `
    --agent_re_spawn true `
    --metabolism "[3.1, 3.1]" `
    --vision "[1, 1]" `
    --endowment "[5, 5]" `
    --log_agent_data true `
    --age "[1000,1000]" `
    --investments_enabled true `
    --lending_enabled false `
    --deposits_enabled false `
    --tag prod *>&1

$run2_duration = (Get-Date) - $run2_start
Write-Host ("`n`t- Investments run finished in {0}" -f $run2_duration.ToString('hh\:mm\:ss')) -ForegroundColor Yellow
Write-Host "-------------------------------------------------------------"


# --- Experiment 3: Investments and Lending Enabled ---
Write-Host "`n[3/4] Running: Lending-Enabled Experiment..." -ForegroundColor Cyan
$run3_start = Get-Date

python -m sugarscape_g1mt.run_batch --run_group "baseline_lending" `
    --total_steps 500 `
    --replications 1 `
    --initial_population "[100,200,300,400]" `
    --agent_re_spawn true `
    --metabolism "[3.1, 3.1]" `
    --vision "[1, 1]" `
    --endowment "[5, 5]" `
    --log_agent_data true `
    --age "[1000,1000]" `
    --investments_enabled true `
    --lending_enabled true `
    --deposits_enabled false `
    --tag prod *>&1

$run3_duration = (Get-Date) - $run3_start
Write-Host ("`n`t- Lending run finished in {0}" -f $run3_duration.ToString('hh\:mm\:ss')) -ForegroundColor Yellow
Write-Host "-------------------------------------------------------------"


# --- Experiment 4: Deposits Enabled ---
Write-Host "`n[4/4] Running: Deposits-Enabled Experiment..." -ForegroundColor Cyan
$run4_start = Get-Date

python -m sugarscape_g1mt.run_batch --run_group "baseline_deposits" `
    --total_steps 500 `
    --replications 1 `
    --initial_population "[100]" `
    --agent_re_spawn true `
    --metabolism "[3.1, 3.1]" `
    --vision "[1, 1]" `
    --endowment "[5, 5]" `
    --log_agent_data true `
    --age "[1000,1000]" `
    --investments_enabled true `
    --lending_enabled true `
    --deposits_enabled true `
    --tag prod *>&1

$run4_duration = (Get-Date) - $run4_start
Write-Host ("`n`t- Deposits run finished in {0}" -f $run4_duration.ToString('hh\:mm\:ss')) -ForegroundColor Yellow
Write-Host "-------------------------------------------------------------"


# --- Calculate and Display Total Runtime ---
$total_end_time = Get-Date
$total_duration = $total_end_time - $total_start_time

Write-Host ("`n>>> Full experiment batch finished at $total_end_time") -ForegroundColor Green
Write-Host ("`nTotal Batch Runtime: {0}" -f $total_duration.ToString('hh\:mm\:ss')) -ForegroundColor Green