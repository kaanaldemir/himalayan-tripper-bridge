$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$toolDirectory = Join-Path $repositoryRoot '.local/tools'
New-Item -ItemType Directory -Force $toolDirectory | Out-Null

function Get-VerifiedTool([string] $Url, [string] $Name, [string] $Sha256) {
    $toolPath = Join-Path $toolDirectory $Name
    if (-not (Test-Path -LiteralPath $toolPath)) {
        Invoke-WebRequest -Uri $Url -OutFile $toolPath
    }
    if ((Get-FileHash -LiteralPath $toolPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Sha256) {
        throw "Hash mismatch for $Name. Do not run this file."
    }
    Write-Output "Verified $Name"
}

Get-VerifiedTool 'https://github.com/1013503897/jadx-headless-mcp/releases/download/v0.7.1/jadx-headless-mcp-0.7.1-all.jar' 'jadx-headless.jar' '6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75'
Get-VerifiedTool 'https://dl.google.com/dl/android/maven2/com/android/tools/build/apksig/8.9.2/apksig-8.9.2.jar' 'apksig.jar' 'c070ed1394629d74641aa0906f60b2ffa1ee77e6366a1f93437f59717b1aeb89'
Write-Output 'A full JDK 17+ is required. No global tools, phone settings, or application configurations were changed.'
