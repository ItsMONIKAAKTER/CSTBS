<#
Synchronize a CLEAN downloaded CSTBS source tree into an EXISTING Git repository.

This deliberately never touches .git, .env, instance/ (SQLite & secrets), .venv,
LICENSE or IDE files. It replaces the tracked source directories so obsolete
historical tests and release notes do not linger after a ZIP overlay.

Preview (no changes):
  .\scripts\sync-to-repository.ps1 -RepoPath 'D:\CSTBS\New folder'
Apply only after backing up the repository/runtime data:
  .\scripts\sync-to-repository.ps1 -RepoPath 'D:\CSTBS\New folder' -Apply
#>
param(
    [Parameter(Mandatory = $true)][string]$RepoPath,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$target = (Resolve-Path $RepoPath).Path
if ($source.TrimEnd('\') -eq $target.TrimEnd('\')) {
    throw 'Extract the downloaded project to a NEW folder. The source and Git repository cannot be the same directory.'
}
if (-not (Test-Path -LiteralPath (Join-Path $target '.git'))) {
    throw "Not a Git repository: $target"
}
$changes = @(git -C $target status --porcelain --untracked-files=normal)
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect repository status.' }
if ($changes.Count -gt 0 -and ($changes | Where-Object { $_ -ne '' })) {
    throw 'Repository contains uncommitted changes. Commit or safely back them up before replacing code.'
}
Write-Host "SOURCE: $source"
Write-Host "TARGET: $target"
Write-Host 'Will replace: .github/, app/, docs/, tests/, scripts/ and root source/config files.'
Write-Host 'Will remove: historical CHANGELOG.md and obsolete tests via full tests/ replacement.'
Write-Host 'Will preserve: .git/, .env, instance/, .venv/, LICENSE, IDE files.'
if (-not $Apply) {
    Write-Host 'DRY RUN — no files changed. Pass -Apply to perform the controlled replacement.'
    return
}
foreach ($folder in @('.github', 'app', 'docs', 'tests', 'scripts')) {
    $dest = Join-Path $target $folder
    $from = Join-Path $source $folder
    if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
    if (Test-Path -LiteralPath $from) { Copy-Item -LiteralPath $from -Destination $dest -Recurse -Force }
}
foreach ($file in @('.env.example','.gitignore','README.md','SECURITY.md',
                   'requirements.txt','config.py','run.py')) {
    Copy-Item -LiteralPath (Join-Path $source $file) -Destination (Join-Path $target $file) -Force
}
$history = Join-Path $target 'CHANGELOG.md'
if (Test-Path -LiteralPath $history) { Remove-Item -LiteralPath $history -Force }
Write-Host 'Source replacement complete. Runtime databases and secrets remain untouched.'
Write-Host "Next: cd '$target'; run the full test suite, inspect 'git status' and commit only after tests pass."
