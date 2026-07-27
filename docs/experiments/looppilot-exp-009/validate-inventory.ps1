param(
    [switch]$WriteInventory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProductCommit = "52173e08ae267700ef62e7e563ab6a50523981ad"
$ProductTree = "82df778e7401f5b0fccacbd81b124664fea080f9"
$ArchiveCommit = "8b6075aaee8e86a6c7905911487e537672a4125b"
$ArchiveTree = "aeb86d86782377d7fac7101f931e14cda9d1fb4a"
$PreregistrationCommit = "5a0347a7bf7161ac992e1dfa1ea86f68b634dc85"
$InventoryPath = Join-Path $PSScriptRoot "EVIDENCE-INVENTORY.tsv"

$ProductPaths = @(
    "apps/frontend/src/console/hooks.ts",
    "apps/frontend/src/shared/api.ts",
    "apps/studio/app/main.py",
    "fantasy_agent/approval_manifest.py",
    "fantasy_agent/artifact_identity.py",
    "fantasy_agent/contracts.py",
    "fantasy_agent/executor.py",
    "fantasy_agent/workflows.py",
    "tests/frontend_approval_manifest_api.test.mjs",
    "tests/test_approval_identity_integration.py",
    "tests/test_creative_review_agent.py",
    "tests/test_executor.py",
    "tests/test_production_spec_runtime.py",
    "tests/test_studio_app.py"
)

$AuthoritativePaths = @(
    ".looppilot/CHECKPOINT.md",
    ".looppilot/LOOP-MAP.md",
    ".looppilot/PROJECT.md",
    ".looppilot/loops/LOOP-001/FINDING-LEDGER.md",
    ".looppilot/loops/LOOP-001/LOOP-CLOSURE.md",
    ".looppilot/loops/LOOP-001/LOOP-CONTRACT.md",
    ".looppilot/loops/LOOP-001/TASK-LEDGER.md"
)

function Invoke-GitLines {
    param([string[]]$Arguments)

    $output = @(& git @Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
    return $output
}

function Get-GitBlobBytes {
    param(
        [string]$Commit,
        [string]$Path
    )

    $objectId = [string](Invoke-GitLines -Arguments @("rev-parse", "${Commit}:$Path") | Select-Object -First 1)
    $objectId = $objectId.Trim()
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "git"
    $startInfo.Arguments = "cat-file blob $objectId"
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    [void]$process.Start()
    $memory = New-Object System.IO.MemoryStream
    $process.StandardOutput.BaseStream.CopyTo($memory)
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw "git cat-file failed for ${Commit}:$Path`: $stderr"
    }
    return ,$memory.ToArray()
}

function Get-Sha256 {
    param([byte[]]$Bytes)

    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($algorithm.ComputeHash($Bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-PhysicalLines {
    param([byte[]]$Bytes)

    if ($Bytes.Length -eq 0) {
        return 0
    }
    $lineCount = 0
    foreach ($value in $Bytes) {
        if ($value -eq 10) {
            $lineCount++
        }
    }
    if ($Bytes[$Bytes.Length - 1] -ne 10) {
        $lineCount++
    }
    return $lineCount
}

function Get-Category {
    param([string]$Path)

    if ($ProductPaths -contains $Path) {
        return "PRODUCT"
    }
    if ($AuthoritativePaths -contains $Path) {
        return "AUTHORITATIVE_GOVERNANCE"
    }
    if ($Path -like ".looppilot/loops/LOOP-001/reviews/*") {
        return "REVIEW"
    }
    if ($Path -like ".looppilot/*") {
        return "SUPPORTING_GOVERNANCE"
    }
    if ($Path -eq "docs/experiments/looppilot-exp-008/POST-BLOCK-ROOT-CAUSE-REVIEW.md") {
        return "RECOVERY"
    }
    if ($Path -like "docs/experiments/looppilot-exp-008/*") {
        return "EVALUATION"
    }
    throw "No inventory category for $Path"
}

function Get-Purpose {
    param([string]$Category)

    switch ($Category) {
        "PRODUCT" { return "INTEGRATION-003 fixed product/test evidence" }
        "AUTHORITATIVE_GOVERNANCE" { return "EXP-008 authority or approved Contract evidence" }
        "SUPPORTING_GOVERNANCE" { return "EXP-008 supporting governance evidence" }
        "REVIEW" { return "Independent or task review evidence" }
        "EVALUATION" { return "EXP-008 evaluation evidence" }
        "RECOVERY" { return "Post-block root-cause and recovery disposition" }
        default { throw "No purpose for category $Category" }
    }
}

function New-InventoryRow {
    param(
        [string]$Commit,
        [string]$Tree,
        [string]$Path
    )

    $bytes = Get-GitBlobBytes -Commit $Commit -Path $Path
    $category = Get-Category -Path $Path
    return [PSCustomObject][ordered]@{
        path = $Path
        category = $category
        source_commit = $Commit
        source_tree = $Tree
        sha256 = Get-Sha256 -Bytes $bytes
        physical_lines = Get-PhysicalLines -Bytes $bytes
        bytes = $bytes.Length
        purpose = Get-Purpose -Category $category
    }
}

$observedProductTree = [string](Invoke-GitLines -Arguments @("rev-parse", "${ProductCommit}^{tree}") | Select-Object -First 1)
if ($observedProductTree.Trim() -ne $ProductTree) {
    throw "Product tree does not match the preregistered tree"
}
$observedArchiveTree = [string](Invoke-GitLines -Arguments @("rev-parse", "${ArchiveCommit}^{tree}") | Select-Object -First 1)
if ($observedArchiveTree.Trim() -ne $ArchiveTree) {
    throw "Archive tree does not match the preregistered tree"
}

$governancePaths = @(Invoke-GitLines -Arguments @("ls-tree", "-r", "--name-only", $ArchiveCommit, "--", ".looppilot"))
$evaluationPaths = @(Invoke-GitLines -Arguments @("ls-tree", "-r", "--name-only", $ArchiveCommit, "--", "docs/experiments/looppilot-exp-008"))

$expectedRows = @()
foreach ($path in ($ProductPaths | Sort-Object)) {
    $expectedRows += New-InventoryRow -Commit $ProductCommit -Tree $ProductTree -Path $path
}
foreach ($path in (($governancePaths + $evaluationPaths) | Sort-Object)) {
    $expectedRows += New-InventoryRow -Commit $ArchiveCommit -Tree $ArchiveTree -Path $path
}

if ($WriteInventory) {
    $header = "path`tcategory`tsource_commit`tsource_tree`tsha256`tphysical_lines`tbytes`tpurpose"
    $lines = @($header)
    foreach ($row in $expectedRows) {
        $lines += @($row.path, $row.category, $row.source_commit, $row.source_tree, $row.sha256,
            $row.physical_lines, $row.bytes, $row.purpose) -join "`t"
    }
    [System.IO.File]::WriteAllLines($InventoryPath, $lines, (New-Object System.Text.UTF8Encoding($false)))
}

if (-not (Test-Path -LiteralPath $InventoryPath)) {
    throw "Missing inventory: $InventoryPath"
}

$actualRows = @(Import-Csv -LiteralPath $InventoryPath -Delimiter "`t")
if ($actualRows.Count -ne $expectedRows.Count) {
    throw "Inventory count mismatch: actual=$($actualRows.Count) expected=$($expectedRows.Count)"
}

$duplicateKeys = @($actualRows | Group-Object source_commit, path | Where-Object Count -ne 1)
if ($duplicateKeys.Count -ne 0) {
    throw "Inventory contains duplicate commit/path members"
}

$expectedByKey = @{}
foreach ($row in $expectedRows) {
    $expectedByKey["$($row.source_commit)`t$($row.path)"] = $row
}

foreach ($actual in $actualRows) {
    $key = "$($actual.source_commit)`t$($actual.path)"
    if (-not $expectedByKey.ContainsKey($key)) {
        throw "Unexpected inventory member: $key"
    }
    $expected = $expectedByKey[$key]
    foreach ($field in @("category", "source_tree", "sha256", "physical_lines", "bytes", "purpose")) {
        if ([string]$actual.$field -cne [string]$expected.$field) {
            throw "Inventory mismatch for $($actual.path) field $field`: actual=$($actual.$field) expected=$($expected.$field)"
        }
    }
}

& git diff --quiet $ProductCommit HEAD -- fantasy_agent tests apps
if ($LASTEXITCODE -ne 0) {
    throw "Product/test/frontend boundary differs from Product HEAD"
}

$membershipLines = @($actualRows | ForEach-Object { "$($_.source_commit)`t$($_.path)" } | Sort-Object)
$membershipBytes = [System.Text.Encoding]::UTF8.GetBytes(($membershipLines -join "`n") + "`n")
$membershipHash = Get-Sha256 -Bytes $membershipBytes

$governanceRows = @($actualRows | Where-Object { $_.path -like ".looppilot/*" })
$evaluationRows = @($actualRows | Where-Object { $_.path -like "docs/experiments/looppilot-exp-008/*" })
$productRows = @($actualRows | Where-Object category -eq "PRODUCT")

Write-Output "Inventory members: $($actualRows.Count)"
Write-Output "Membership SHA-256: $membershipHash"
Write-Output "Governance: files=$($governanceRows.Count) lines=$(($governanceRows | Measure-Object physical_lines -Sum).Sum) bytes=$(($governanceRows | Measure-Object bytes -Sum).Sum)"
Write-Output "Evaluation: files=$($evaluationRows.Count) lines=$(($evaluationRows | Measure-Object physical_lines -Sum).Sum) bytes=$(($evaluationRows | Measure-Object bytes -Sum).Sum)"
Write-Output "Product evidence: files=$($productRows.Count) lines=$(($productRows | Measure-Object physical_lines -Sum).Sum) bytes=$(($productRows | Measure-Object bytes -Sum).Sum)"

& git diff --quiet $PreregistrationCommit -- $InventoryPath
if ($LASTEXITCODE -ne 0) {
    throw "Frozen inventory file differs from the preregistration commit"
}
& git diff --quiet $ArchiveCommit HEAD -- .looppilot docs/experiments/looppilot-exp-008
if ($LASTEXITCODE -ne 0) {
    throw "Archived EXP-008 evidence differs from the archival base"
}

$governanceNames = @(
    "CHECKLIST.md",
    "RECOVERY-CONTRACT.md",
    "REVIEW-CONTRACT.md",
    "REVIEW.md",
    "STATE.md"
)
$recoveryEvaluationNames = @(
    "EVIDENCE-INVENTORY.tsv",
    "EVALUATION-SCORECARD.md",
    "EXPERIMENT-PLAN.md",
    "RECOVERY-ANALYSIS.md",
    "RESULTS.md",
    "validate-inventory.ps1"
)
$expectedRecoveryNames = @(($governanceNames + $recoveryEvaluationNames) | Sort-Object)
$actualRecoveryNames = @(Get-ChildItem -LiteralPath $PSScriptRoot -File | Select-Object -ExpandProperty Name | Sort-Object)
if (@(Compare-Object $expectedRecoveryNames $actualRecoveryNames).Count -ne 0) {
    throw "EXP-009 artifact membership differs from the contracted 5 governance / 6 evaluation files"
}

function Measure-LocalFiles {
    param([string[]]$Names)

    $totalLines = 0
    $totalBytes = 0
    foreach ($name in $Names) {
        $bytes = [System.IO.File]::ReadAllBytes((Join-Path $PSScriptRoot $name))
        $totalBytes += $bytes.Length
        $totalLines += Get-PhysicalLines -Bytes $bytes
    }
    return [PSCustomObject]@{ files = $Names.Count; lines = $totalLines; bytes = $totalBytes }
}

$recoveryGovernance = Measure-LocalFiles -Names $governanceNames
$recoveryEvaluation = Measure-LocalFiles -Names $recoveryEvaluationNames
$stalePattern = "R2 pending|TASK-010 revision 2 under review|finish TASK-010 revision 2|final pending R2|EXP-008 Status: active|PENDING-CANDIDATE-FREEZE|pending candidate freeze|Candidate commit/tree: pending"
$staleHits = @(Get-ChildItem -LiteralPath $PSScriptRoot -File -Filter *.md | Select-String -Pattern $stalePattern -CaseSensitive:$false)
if ($staleHits.Count -ne 0) {
    throw "New EXP-009 artifacts contain stale present-tense historical claims"
}

Write-Output "EXP-009 governance: files=$($recoveryGovernance.files) lines=$($recoveryGovernance.lines) bytes=$($recoveryGovernance.bytes)"
Write-Output "EXP-009 evaluation: files=$($recoveryEvaluation.files) lines=$($recoveryEvaluation.lines) bytes=$($recoveryEvaluation.bytes)"
Write-Output "RESULT inventory=PASS count=PASS membership=PASS sha256=PASS lines=PASS bytes=PASS product_boundary=PASS archive_boundary=PASS stale_scan=PASS recovery_artifacts=PASS"
