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

function New-Fixture([string]$Name, [switch]$Shared, [int]$SchemaVersion = 2, [string]$Case = $caseId) {
    $directory = Join-Path $root "$Name [case files]"
    $paths = @{
        CaseId = $Case
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
        case_id = $paths.CaseId
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

function Write-FixtureReceipt([hashtable]$Fixture, [string]$Check, [hashtable]$Override = @{}) {
    $path = Join-Path $Fixture.Receipts "$Check.json"
    $receipt = @{
        schema_version = $Fixture.SchemaVersion
        case_id = $Fixture.CaseId
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
    foreach ($name in $Override.Keys) { $receipt[$name] = $Override[$name] }
    Write-JsonFile $path $receipt
}

function Invoke-Verifier {
    param(
        [hashtable]$Fixture,
        [switch]$NoFlags,
        [string]$EnvironmentRun,
        [string]$EnvironmentAttempt,
        [switch]$WriteSummary,
        [string]$CatalogPath = $catalog,
        [string]$WorkingDirectory = $checkout,
        [string]$VerifierPath = $verifier,
        [string]$Interpreter = $Python,
        [string]$LogPath
    )

    $arguments = @('-B', '-X', 'utf8', $VerifierPath, '--catalog', $CatalogPath, '--case', $Fixture.CaseFile,
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
    Push-Location -LiteralPath $WorkingDirectory
    try {
        foreach ($name in $variables.Keys) {
            [Environment]::SetEnvironmentVariable($name, $variables[$name])
        }
        $output = if ($LogPath) {
            & $Interpreter @arguments 2>&1 | Tee-Object -LiteralPath $LogPath
        }
        else {
            & $Interpreter @arguments 2>&1
        }
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
| FIXTURE-002 | Vault fixture | P1 | Verify other case | Distinguish case identity |
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



    Test-Case 'GHQ-PS-012 rejects evidence from a different run or attempt' {
        $fixture = New-Fixture 'run and attempt'
        Write-FixtureReceipt $fixture 'read'
        foreach ($field in @('run_id', 'attempt')) {
            Write-FixtureReceipt $fixture 'build' @{ $field = '91' }
            Assert-Verdict (Invoke-Verifier $fixture) 1 "$field does not match"
        }
        Write-FixtureReceipt $fixture 'build'
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-014 rejects an otherwise identical untracked catalog' {
        $fixture = New-Fixture 'untracked catalog'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $duplicate = Join-Path $fixtureVault 'untracked.md'
        Copy-Item -LiteralPath $catalog -Destination $duplicate
        Assert-Verdict (Invoke-Verifier $fixture -CatalogPath $duplicate) 1 'source must be tracked'
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-018 restricts verification to the intended Git root' {
        $fixture = New-Fixture 'intended checkout root'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        Assert-Verdict (Invoke-Verifier $fixture -WorkingDirectory $fixtureVault) 1 'intended Git checkout root'
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-016 rejects duplicate receipts with different filenames' {
        $fixture = New-Fixture 'duplicate record'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $extra = Join-Path $fixture.Receipts 'other.json'
        Copy-Item -LiteralPath (Join-Path $fixture.Receipts 'build.json') -Destination $extra
        Assert-Verdict (Invoke-Verifier $fixture) 1 '| build | DUPLICATE |'
        Remove-Item -LiteralPath $extra
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-017 rejects valid nonpassing receipt statuses' {
        $fixture = New-Fixture 'nonpassing receipt'
        Write-FixtureReceipt $fixture 'read'
        foreach ($outcome in @('skip', 'blocked', 'fail')) {
            Write-FixtureReceipt $fixture 'build' @{ status = $outcome }
            Assert-Verdict (Invoke-Verifier $fixture) 1 "**Overall: FAIL**"
            Assert-Verdict (Invoke-Verifier $fixture) 1 "| build | $($outcome.ToUpperInvariant()) |"
        }
    }

    Test-Case 'GHQ-PS-024 rejects mixed v1 and v2 receipts in a v2 case' {
        $fixture = New-Fixture 'mixed versions'
        Write-FixtureReceipt $fixture 'read'
        $fixture.SchemaVersion = 1
        Write-FixtureReceipt $fixture 'build'
        Assert-Verdict (Invoke-Verifier $fixture) 1 '| build | INVALID |'
        $fixture.SchemaVersion = 2
        Write-FixtureReceipt $fixture 'build'
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-025 rejects noncanonical execution identity strings' {
        $fixture = New-Fixture 'noncanonical run metadata'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        foreach ($invalid in @('0', '01', 'text')) {
            Assert-Verdict (Invoke-Verifier $fixture -NoFlags -EnvironmentRun $invalid -EnvironmentAttempt $attempt) 1 'run ID and attempt must be positive'
            Assert-Verdict (Invoke-Verifier $fixture -NoFlags -EnvironmentRun $runId -EnvironmentAttempt $invalid) 1 'run ID and attempt must be positive'
        }
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-026 rejects a complete but undeclared check receipt' {
        $fixture = New-Fixture 'undeclared record'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        Write-FixtureReceipt $fixture 'other'
        Assert-Verdict (Invoke-Verifier $fixture) 1 'Found an undeclared check receipt.'
        Remove-Item -LiteralPath (Join-Path $fixture.Receipts 'other.json')
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-027 rejects a partially written receipt without losing the prior check' {
        $fixture = New-Fixture 'partial receipt'
        Write-FixtureReceipt $fixture 'build'
        $build = Join-Path $fixture.Receipts 'build.json'
        $digest = (Get-FileHash -LiteralPath $build).Hash
        Set-Content -LiteralPath (Join-Path $fixture.Receipts 'read.json') -Value '{"case_id":'
        Assert-Verdict (Invoke-Verifier $fixture) 1 'Found an unreadable or invalid receipt.'
        if ((Get-FileHash -LiteralPath $build).Hash -ne $digest) { throw 'Previous evidence changed.' }
        Write-FixtureReceipt $fixture 'read'
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-030 follows the pinned receipt decoder encoding profile' {
        $fixture = New-Fixture 'receipt encoding'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $receiptPath = Join-Path $fixture.Receipts 'read.json'
        $valid = [IO.File]::ReadAllText($receiptPath)
        [IO.File]::WriteAllText($receiptPath, $valid, [Text.Encoding]::Unicode)
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
        $bytes = [IO.File]::ReadAllBytes($receiptPath)
        [IO.File]::WriteAllBytes($receiptPath, $bytes[0..($bytes.Length - 2)])
        Assert-Verdict (Invoke-Verifier $fixture) 1 'Found an unreadable or invalid receipt.'
    }

    Test-Case 'GHQ-PS-013 verifies from a real Unicode checkout path' {
        $clone = Join-Path $root 'café [git checkout]'
        Invoke-FixtureGit worktree add --quiet --detach $clone
        $fixture = New-Fixture 'événement [fixture]'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $catalogCopy = Join-Path $clone 'test-vault/catalog [cases].md'
        $verifierCopy = Join-Path $clone 'test-vault/verify_receipts.py'
        Assert-Verdict (Invoke-Verifier $fixture -WorkingDirectory $clone -CatalogPath $catalogCopy -VerifierPath $verifierCopy) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-019 distinguishes CRLF and LF plan bytes' {
        $fixture = New-Fixture 'case line endings'
        $lf = [IO.File]::ReadAllText($fixture.CaseFile).Replace("`r`n", "`n")
        [IO.File]::WriteAllText($fixture.CaseFile, $lf.Replace("`n", "`r`n"))
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
        [IO.File]::WriteAllText($fixture.CaseFile, $lf)
        Assert-Verdict (Invoke-Verifier $fixture) 1 'case_plan_sha256 does not match'
    }

    Test-Case 'GHQ-PS-020 preserves a native verifier failure through Tee-Object' {
        $fixture = New-Fixture 'native exit through tee'
        Write-FixtureReceipt $fixture 'build'
        $log = Join-Path $root 'native-failure.log'
        Assert-Verdict (Invoke-Verifier $fixture -LogPath $log) 1 '| read | MISSING |'
        if (-not (Get-Content -LiteralPath $log -Raw).Contains('**Overall: FAIL**')) { throw 'Native failure was lost' }
        Write-FixtureReceipt $fixture 'read'
        Assert-Verdict (Invoke-Verifier $fixture -LogPath $log) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-021 restores the caller location and metadata after native launch fails' {
        $fixture = New-Fixture 'environment restore'
        $location = (Get-Location).Path
        $savedRun = $env:GITHUB_RUN_ID
        $savedAttempt = $env:GITHUB_RUN_ATTEMPT
        $env:GITHUB_RUN_ID = '321'
        $env:GITHUB_RUN_ATTEMPT = '7'
        try {
            $failed = $false
            try {
                Invoke-Verifier $fixture -EnvironmentRun '888' -EnvironmentAttempt '6' -Interpreter (Join-Path $root 'missing-runtime.exe')
            }
            catch [System.Management.Automation.CommandNotFoundException] {
                $failed = $true
            }
            if (-not $failed -or (Get-Location).Path -ne $location -or
                $env:GITHUB_RUN_ID -ne '321' -or $env:GITHUB_RUN_ATTEMPT -ne '7') { throw 'Caller context was not restored' }
            Write-FixtureReceipt $fixture 'build'
            Write-FixtureReceipt $fixture 'read'
            Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
        }
        finally {
            $env:GITHUB_RUN_ID = $savedRun
            $env:GITHUB_RUN_ATTEMPT = $savedAttempt
        }
    }

    Test-Case 'GHQ-PS-022 diagnoses a receipt directory that was replaced with a file' {
        $fixture = New-Fixture 'invalid receipt directory'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $valid = $fixture.Receipts
        $path = Join-Path $root 'file-instead-of-receipt-directory'
        [IO.File]::WriteAllText($path, 'unchanged')
        $fixture.Receipts = $path
        Assert-Verdict (Invoke-Verifier $fixture) 1 'Receipt directory is missing or invalid'
        if ([IO.File]::ReadAllText($path) -ne 'unchanged') { throw 'Unexpected write to invalid receipt target' }
        $fixture.Receipts = $valid
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-023 binds the receipt to a linked worktree HEAD' {
        $linked = Join-Path $root 'alternate worktree'
        Invoke-FixtureGit worktree add --quiet --detach $linked
        $fixture = New-Fixture 'linked worktree identity'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        Invoke-FixtureGit -c user.name=Fixture -c user.email=fixture@example.invalid -c commit.gpgsign=false commit --allow-empty -qm 'Advance main worktree only'
        $script:fixtureHead = Invoke-FixtureGit rev-parse HEAD
        Assert-Verdict (Invoke-Verifier $fixture) 1 'checkout_sha'
        Assert-Verdict (Invoke-Verifier $fixture -WorkingDirectory $linked -CatalogPath (Join-Path $linked 'test-vault/catalog [cases].md') -VerifierPath (Join-Path $linked 'test-vault/verify_receipts.py')) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-029 treats a failed step-summary write as a native failure' {
        $fixture = New-Fixture 'summary write failure'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $regular = $fixture.Summary
        $fixture.Summary = $fixture.Receipts
        $failure = Invoke-Verifier $fixture -WriteSummary
        if ($failure.ExitCode -eq 0) { throw 'An invalid summary target returned success' }
        $fixture.Summary = $regular
        Assert-Verdict (Invoke-Verifier $fixture -WriteSummary) 0 '**Overall: PASS**'
        if (-not (Get-Content -LiteralPath $regular -Raw).Contains('**Overall: PASS**')) { throw 'Missing valid summary evidence' }
    }

    Test-Case 'GHQ-PS-031 distinguishes launch failure from a verifier verdict' {
        $fixture = New-Fixture 'missing runtime'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        $failed = $false
        try {
            Invoke-Verifier $fixture -WriteSummary -Interpreter (Join-Path $root 'does-not-exist.exe')
        }
        catch [System.Management.Automation.CommandNotFoundException] {
            $failed = $true
        }
        if (-not $failed -or (Test-Path -LiteralPath $fixture.Summary)) { throw 'A missing interpreter produced a verdict' }
        Assert-Verdict (Invoke-Verifier $fixture -WriteSummary) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-035 discovers lowercase receipt extensions consistently' {
        $fixture = New-Fixture 'receipt extension'
        Write-FixtureReceipt $fixture 'build'
        Write-FixtureReceipt $fixture 'read'
        Move-Item -LiteralPath (Join-Path $fixture.Receipts 'read.json') -Destination (Join-Path $fixture.Receipts 'candidate.JSON')
        Assert-Verdict (Invoke-Verifier $fixture) 1 '| read | MISSING |'
        Move-Item -LiteralPath (Join-Path $fixture.Receipts 'candidate.JSON') -Destination (Join-Path $fixture.Receipts 'read.json')
        Assert-Verdict (Invoke-Verifier $fixture) 0 '**Overall: PASS**'
    }

    Test-Case 'GHQ-PS-036 distinguishes case identity even when required checks match' {
        $original = New-Fixture 'original case'
        Write-FixtureReceipt $original 'build'
        Write-FixtureReceipt $original 'read'
        Assert-Verdict (Invoke-Verifier $original) 0 '**Overall: PASS**'
        $other = New-Fixture 'independent case' -Case 'FIXTURE-002'
        $other.Receipts = $original.Receipts
        Assert-Verdict (Invoke-Verifier $other) 1 'case_id does not match'
        Write-FixtureReceipt $other 'build'
        Write-FixtureReceipt $other 'read'
        Assert-Verdict (Invoke-Verifier $other) 0 '**Overall: PASS**'
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
