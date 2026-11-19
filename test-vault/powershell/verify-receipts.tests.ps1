[CmdletBinding()]
param([string]$Python = 'python')

$ErrorActionPreference = 'Stop'
# Several cases intentionally exercise a nonzero exit from Python.
$PSNativeCommandUseErrorActionPreference = $false
$vault = Join-Path $PSScriptRoot '..'
$root = Join-Path ([IO.Path]::GetTempPath()) ('ghq vault [fixture] ' + [guid]::NewGuid())
$checkout = Join-Path $root 'git checkout [literal]'
$fixtureVault = Join-Path $checkout 'test-vault'
$verifier = Join-Path $fixtureVault 'verify_receipts.py'
$catalog = Join-Path $fixtureVault 'catalog [cases].md'
$caseId = 'FIXTURE-001'
$runId = '94501'
$attempt = '2'
$failures = [System.Collections.Generic.List[string]]::new()

function Invoke-FixtureGit {
    $result = & git -C $checkout @args
    if ($LASTEXITCODE -ne 0) { throw "Git fixture command failed: $args" }
    $result
}

function Write-JsonFile([string]$Path, [hashtable]$Value) {
    $Value | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
}

function New-Fixture([string]$Name, [switch]$Shared, [int]$SchemaVersion = 2) {
    $directory = Join-Path $root "$Name [case files]"
    $paths = @{
        CaseFile = Join-Path $directory 'case [definition].json'
        Receipts = Join-Path $directory 'receipt [output]'
        Summary = Join-Path $directory 'job [summary].md'
        SchemaVersion = $SchemaVersion
        Evidence = $null
        EvidenceDigest = $null
    }
    [void][IO.Directory]::CreateDirectory($paths.Receipts)
    Write-JsonFile $paths.CaseFile @{
        schema_version = $SchemaVersion
        case_id = $caseId
        required_checks = @('build', 'read')
        shared_evidence = [bool]$Shared
    }
    if ($Shared) {
        $paths.Evidence = Join-Path $directory 'graph [evidence].json'
        [IO.File]::WriteAllBytes($paths.Evidence, [byte[]]@(123, 125, 10))
        $paths.EvidenceDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $paths.Evidence).Hash.ToLowerInvariant()
    }
    $paths
}

function Write-FixtureReceipt([hashtable]$Fixture, [string]$Check) {
    $path = Join-Path $Fixture.Receipts "$Check.json"
    $receipt = @{
        schema_version = $Fixture.SchemaVersion
        case_id = $caseId
        check_id = $Check
        checkout_sha = $script:fixtureHead
        run_id = $runId
        attempt = $attempt
        evidence_sha256 = $Fixture.EvidenceDigest
        environment = @{ os = 'synthetic-fixture'; runtime = 'synthetic-fixture' }
        status = 'pass'
    }
    if ($Fixture.SchemaVersion -eq 2) {
        $receipt.case_plan_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Fixture.CaseFile).Hash.ToLowerInvariant()
    }
    Write-JsonFile $path $receipt
}

function Invoke-Verifier {
    param(
        [hashtable]$Fixture,
        [switch]$NoFlags,
        [string]$EnvironmentRun,
        [string]$EnvironmentAttempt,
        [switch]$WriteSummary
    )

    $arguments = @('-B', '-X', 'utf8', $verifier, '--catalog', $catalog, '--case', $Fixture.CaseFile,
        '--receipts', $Fixture.Receipts)
    if (-not $NoFlags) { $arguments += @('--run-id', $runId, '--attempt', $attempt) }
    if ($Fixture.Evidence) { $arguments += @('--evidence', $Fixture.Evidence) }
    $variables = @{
        GITHUB_RUN_ID = $EnvironmentRun
        GITHUB_RUN_ATTEMPT = $EnvironmentAttempt
        GITHUB_STEP_SUMMARY = if ($WriteSummary) { $Fixture.Summary } else { $null }
    }
    $previous = @{}
    foreach ($name in $variables.Keys) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name)
    }
    Push-Location -LiteralPath $checkout
    try {
        foreach ($name in $variables.Keys) {
            [Environment]::SetEnvironmentVariable($name, $variables[$name])
        }
        $output = & $Python @arguments
        $exitCode = $LASTEXITCODE
        @{ ExitCode = $exitCode; Text = ($output -join [Environment]::NewLine) }
    }
    finally {
        foreach ($name in $previous.Keys) {
            [Environment]::SetEnvironmentVariable($name, $previous[$name])
        }
        Pop-Location
    }
}

function Assert-Verdict([hashtable]$Result, [int]$ExitCode, [string]$Fragment) {
    if ($Result.ExitCode -ne $ExitCode -or -not $Result.Text.Contains($Fragment)) {
        throw "Expected exit $ExitCode and '$Fragment'. Got exit $($Result.ExitCode) and output: $($Result.Text)"
    }
}

function Test-Case([string]$Name, [scriptblock]$Body) {
    try {
        & $Body
        Write-Output "PASS $Name"
    }
    catch {
        $failures.Add("$Name - $_")
        Write-Output "FAIL $Name - $_"
    }
}

try {
    [void][IO.Directory]::CreateDirectory($fixtureVault)
    Invoke-FixtureGit init -q
    foreach ($file in @('verify_receipts.py', 'validate_catalog.py', 'source_commit.py')) {
        Copy-Item -LiteralPath (Join-Path $vault $file) -Destination $fixtureVault
    }
    @"
| Case | Area | Priority | Suggested implementation | Expected outcome |
|---|---|---|---|---|
| $caseId | Vault fixture | P1 | Invoke verifier | Check portable invocation |
"@ | Set-Content -LiteralPath $catalog -Encoding utf8NoBOM
    Invoke-FixtureGit add -- test-vault
    Invoke-FixtureGit -c user.name=Fixture -c user.email=fixture@example.invalid -c commit.gpgsign=false commit -qm 'Receipt fixture'
    $script:fixtureHead = Invoke-FixtureGit rev-parse HEAD

    Test-Case 'GHQ-PS-001 passes literal Windows-style argument paths to the verifier' {
        $fixture = New-Fixture 'literal paths'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $result = Invoke-Verifier $fixture
        Assert-Verdict $result 0 '**Overall: PASS**'
        Assert-Verdict $result 0 "Checkout: $script:fixtureHead"
    }

    Test-Case 'GHQ-PS-002 preserves the native exit code for a missing check' {
        $fixture = New-Fixture 'missing check'
        Write-FixtureReceipt $fixture 'build'
        $result = Invoke-Verifier $fixture
        Assert-Verdict $result 1 '| read | MISSING |'
        Assert-Verdict $result 1 '**Overall: FAIL**'
    }

    Test-Case 'GHQ-PS-003 appends pass and fail verdicts to the literal Actions summary path' {
        $fixture = New-Fixture 'step summary'
        Set-Content -LiteralPath $fixture.Summary -Value 'Existing summary' -Encoding utf8NoBOM
        Write-FixtureReceipt $fixture 'build'
        Assert-Verdict (Invoke-Verifier $fixture -WriteSummary) 1 '**Overall: FAIL**'
        Write-FixtureReceipt $fixture 'read'
        Assert-Verdict (Invoke-Verifier $fixture -WriteSummary) 0 '**Overall: PASS**'
        $summary = Get-Content -LiteralPath $fixture.Summary -Raw
        if (-not $summary.StartsWith('Existing summary') -or -not $summary.Contains('**Overall: FAIL**') -or
            $summary.IndexOf('**Overall: PASS**') -lt $summary.IndexOf('**Overall: FAIL**')) {
            throw "Expected both verdicts appended after the existing summary: $summary"
        }
    }

    Test-Case 'GHQ-PS-004 supplies the run and attempt through the child environment' {
        $fixture = New-Fixture 'environment identity'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $result = Invoke-Verifier $fixture -NoFlags -EnvironmentRun $runId -EnvironmentAttempt $attempt
        Assert-Verdict $result 0 "Run: $runId"
        Assert-Verdict $result 0 "Attempt: $attempt"
    }

    Test-Case 'GHQ-PS-005 preserves explicit run and attempt flags over inherited values' {
        $fixture = New-Fixture 'explicit identity'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $result = Invoke-Verifier $fixture -EnvironmentRun '111' -EnvironmentAttempt '9'
        Assert-Verdict $result 0 "Run: $runId"
        Assert-Verdict $result 0 "Attempt: $attempt"
    }

    Test-Case 'GHQ-PS-006 hands off the exact evidence bytes' {
        $fixture = New-Fixture 'shared bytes' -Shared
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
        [IO.File]::WriteAllBytes($fixture.Evidence, [byte[]]@(91, 93, 10))
        Assert-Verdict (Invoke-Verifier $fixture) 1 'evidence_sha256 does not match'
    }

    Test-Case 'GHQ-PS-007 surfaces a missing run identity in local execution' {
        $fixture = New-Fixture 'no identity'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        Assert-Verdict (Invoke-Verifier $fixture -NoFlags) 1 'run ID and attempt must be positive'
        if (Test-Path -LiteralPath $fixture.Summary) { throw 'Local invocation created a step summary' }
    }

    Test-Case 'GHQ-PS-008 rejects receipts copied from an earlier checkout' {
        $fixture = New-Fixture 'stale checkout'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        Invoke-FixtureGit -c user.name=Fixture -c user.email=fixture@example.invalid -c commit.gpgsign=false commit --allow-empty -qm 'Advance fixture checkout'
        $script:fixtureHead = Invoke-FixtureGit rev-parse HEAD
        $result = Invoke-Verifier $fixture
        Assert-Verdict $result 1 'checkout_sha does not match'
    }

    Test-Case 'GHQ-PS-009 binds v2 receipts to the exact case plan bytes' {
        $fixture = New-Fixture 'v2 case plan'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $result = Invoke-Verifier $fixture
        Assert-Verdict $result 0 '**Overall: PASS**'
        Assert-Verdict $result 0 'Case plan SHA-256:'
        [IO.File]::AppendAllText($fixture.CaseFile, "`n")
        Assert-Verdict (Invoke-Verifier $fixture) 1 'case_plan_sha256 does not match'
    }

    Test-Case 'GHQ-PS-010 verifies legacy v1 receipts after the upgrade' {
        $fixture = New-Fixture 'legacy receipt' -SchemaVersion 1
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $result = Invoke-Verifier $fixture
        Assert-Verdict $result 0 '**Overall: PASS**'
        Assert-Verdict $result 0 'Legacy receipt v1'
    }

    Test-Case 'GHQ-PS-011 rejects tracked checkout changes before accepting receipts' {
        $fixture = New-Fixture 'dirty checkout'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
        [IO.File]::AppendAllText($catalog, "`n")
        Assert-Verdict (Invoke-Verifier $fixture) 1 'commit tracked changes before writing or verifying receipts'
    }
}
finally {
    Remove-Item -LiteralPath $root -Recurse -Force
}

if ($failures.Count -gt 0) {
    Write-Output "$($failures.Count) PowerShell receipt cases failed."
    exit 1
}
exit 0
