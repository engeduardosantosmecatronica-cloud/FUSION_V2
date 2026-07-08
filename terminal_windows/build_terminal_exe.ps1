param(
    [string]$Configuration = "Release",
    [string]$Runtime = "win-x64",
    [switch]$SelfContained
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Project = Join-Path $PSScriptRoot "FusionTerminalWindows.csproj"
$PublishDir = Join-Path $Root "dist\FusionTerminalWindows"

$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if (-not $dotnet -and (Test-Path "C:\Program Files\dotnet\dotnet.exe")) {
    $dotnet = Get-Item "C:\Program Files\dotnet\dotnet.exe"
}

if (-not $dotnet) {
    Write-Host "dotnet nao encontrado. Instale o .NET SDK antes de publicar o terminal."
    exit 1
}

if (Test-Path $PublishDir) {
    Remove-Item -LiteralPath $PublishDir -Recurse -Force
}
New-Item -ItemType Directory -Path $PublishDir | Out-Null

$args = @(
    "publish",
    $Project,
    "-c", $Configuration,
    "-r", $Runtime,
    "-o", $PublishDir,
    "/p:PublishSingleFile=true",
    "/p:IncludeNativeLibrariesForSelfExtract=true"
)

if ($SelfContained) {
    $args += "--self-contained"
    $args += "true"
}
else {
    $args += "--self-contained"
    $args += "false"
}

& $dotnet.Source @args

Write-Host ""
Write-Host "Executavel gerado em:"
Write-Host (Join-Path $PublishDir "FusionTerminalWindows.exe")
Write-Host ""
Write-Host "Abra com dois cliques para iniciar o painel Fusion."
