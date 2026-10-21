<#
.SYNOPSIS
    Publish the showcase to GitHub Pages.

.DESCRIPTION
    Copies showcase/site onto a gh-pages branch and pushes it. GitHub Pages
    serves that branch at https://<user>.github.io/<repo>/.

    The site is static and has no build step, so this is the whole deploy.
    The branch is a build artefact: showcase/site stays the single source of
    truth, and re-running this script republishes it.

.EXAMPLE
    .\scripts\deploy_pages.ps1
#>
[CmdletBinding()]
param(
    [string]$Repo = "aswathas/TradeMCP",
    [string]$Branch = "gh-pages"
)

$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
$site = Join-Path $root "showcase\site"
if (-not (Test-Path (Join-Path $site "index.html"))) {
    throw "showcase/site/index.html is missing - nothing to publish."
}

$git = (Get-Command git -ErrorAction SilentlyContinue).Source
if (-not $git) { $git = "C:\Program Files\Git\cmd\git.exe" }
if (-not (Test-Path $git)) { throw "git not found on PATH." }

$stage = Join-Path ([System.IO.Path]::GetTempPath()) ("trademcp-pages-" + [guid]::NewGuid().ToString("N"))
$url = "https://github.com/$Repo.git"

Write-Host "Cloning $url ..."
& $git clone --quiet --depth 1 --branch main $url $stage
if ($LASTEXITCODE -ne 0) { throw "clone failed" }

try {
    Write-Host "Rebuilding $Branch from showcase/site ..."
    & $git -C $stage checkout --quiet --orphan $Branch
    & $git -C $stage rm --quiet -r -f .
    if ($LASTEXITCODE -ne 0) { throw "could not clear the branch" }

    Copy-Item -Path (Join-Path $site "*") -Destination $stage -Recurse -Force -ErrorAction Stop

    & $git -C $stage add -A
    & $git -C $stage -c user.name="aswathas" -c user.email="46263167+aswathas@users.noreply.github.com" `
        commit --quiet -m "Deploy showcase to GitHub Pages"
    if ($LASTEXITCODE -ne 0) { throw "commit failed" }

    Write-Host "Pushing $Branch ..."
    & $git -C $stage push --quiet --force origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "push failed" }
}
finally {
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Published. Point GitHub Pages at the $Branch branch (root)."
