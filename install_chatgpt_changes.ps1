param(
    [string]$KenshiPath = ""
)

$ErrorActionPreference = "Stop"
$modName = "Vampire Race - Blood Feeding"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$requiredFiles = @(
    "Vampire Race - Blood Feeding.mod",
    "interiors.level",
    "leveldata.level",
    "zone.25.32.zone",
    "zone.25.33.zone",
    "zone.26.32.zone",
    "zone.26.33.zone"
)

function Test-KenshiFolder {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Container)) {
        return $false
    }

    return (
        (Test-Path -LiteralPath (Join-Path $Path "kenshi_x64.exe") -PathType Leaf) -or
        (Test-Path -LiteralPath (Join-Path $Path "kenshi.exe") -PathType Leaf) -or
        (Test-Path -LiteralPath (Join-Path $Path "mods") -PathType Container)
    )
}

function Add-UniquePath {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }

    $expanded = [Environment]::ExpandEnvironmentVariables($Path.Trim().Trim('"'))
    if (Test-KenshiFolder $expanded) {
        $resolved = (Resolve-Path -LiteralPath $expanded).Path
        if (-not $List.Contains($resolved)) {
            $List.Add($resolved)
        }
    }
}

function Find-KenshiFolders {
    $results = [System.Collections.Generic.List[string]]::new()

    $uninstallKeys = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 233860",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 233860"
    )
    foreach ($key in $uninstallKeys) {
        try {
            $installLocation = (Get-ItemProperty -LiteralPath $key -ErrorAction Stop).InstallLocation
            Add-UniquePath $results $installLocation
        }
        catch {
            # The key is optional; Steam libraries are checked below as well.
        }
    }

    $steamRoots = [System.Collections.Generic.List[string]]::new()
    $registryKeys = @(
        "HKCU:\Software\Valve\Steam",
        "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam"
    )
    foreach ($key in $registryKeys) {
        try {
            $properties = Get-ItemProperty -LiteralPath $key -ErrorAction Stop
            foreach ($property in @("SteamPath", "InstallPath")) {
                $value = $properties.$property
                if (-not [string]::IsNullOrWhiteSpace($value) -and -not $steamRoots.Contains($value)) {
                    $steamRoots.Add($value)
                }
            }
        }
        catch {
            # Continue with the standard Steam locations.
        }
    }

    foreach ($standardRoot in @(
        "${env:ProgramFiles(x86)}\Steam",
        "$env:ProgramFiles\Steam"
    )) {
        if (-not [string]::IsNullOrWhiteSpace($standardRoot) -and -not $steamRoots.Contains($standardRoot)) {
            $steamRoots.Add($standardRoot)
        }
    }

    $libraryRoots = [System.Collections.Generic.List[string]]::new()
    foreach ($steamRoot in $steamRoots) {
        if ([string]::IsNullOrWhiteSpace($steamRoot) -or -not (Test-Path -LiteralPath $steamRoot -PathType Container)) {
            continue
        }

        if (-not $libraryRoots.Contains($steamRoot)) {
            $libraryRoots.Add($steamRoot)
        }

        $libraryFile = Join-Path $steamRoot "steamapps\libraryfolders.vdf"
        if (Test-Path -LiteralPath $libraryFile -PathType Leaf) {
            $content = Get-Content -LiteralPath $libraryFile -Raw
            foreach ($match in [regex]::Matches($content, '"path"\s+"([^"]+)"')) {
                $libraryPath = $match.Groups[1].Value -replace '\\\\', '\'
                if (-not $libraryRoots.Contains($libraryPath)) {
                    $libraryRoots.Add($libraryPath)
                }
            }
        }
    }

    foreach ($libraryRoot in $libraryRoots) {
        Add-UniquePath $results (Join-Path $libraryRoot "steamapps\common\Kenshi")
    }

    return $results
}

Write-Host ""
Write-Host "Coven City test-branch installer" -ForegroundColor Cyan
Write-Host "---------------------------------" -ForegroundColor Cyan

foreach ($file in $requiredFiles) {
    $source = Join-Path $scriptRoot $file
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Required file is missing from the extracted branch folder: $file"
    }
}

if (-not [string]::IsNullOrWhiteSpace($KenshiPath)) {
    $KenshiPath = $KenshiPath.Trim().Trim('"')
    if (-not (Test-KenshiFolder $KenshiPath)) {
        throw "The supplied Kenshi path is not valid: $KenshiPath"
    }
    $KenshiPath = (Resolve-Path -LiteralPath $KenshiPath).Path
}
else {
    $found = @(Find-KenshiFolders)
    if ($found.Count -eq 1) {
        $KenshiPath = $found[0]
    }
    elseif ($found.Count -gt 1) {
        Write-Host "More than one Kenshi installation was found:"
        for ($index = 0; $index -lt $found.Count; $index++) {
            Write-Host "  [$($index + 1)] $($found[$index])"
        }
        $selection = Read-Host "Enter the number to use"
        $selectionNumber = 0
        if (-not [int]::TryParse($selection, [ref]$selectionNumber) -or $selectionNumber -lt 1 -or $selectionNumber -gt $found.Count) {
            throw "Invalid selection."
        }
        $KenshiPath = $found[$selectionNumber - 1]
    }
    else {
        $enteredPath = Read-Host "Kenshi was not detected. Paste the folder containing kenshi_x64.exe"
        $enteredPath = $enteredPath.Trim().Trim('"')
        if (-not (Test-KenshiFolder $enteredPath)) {
            throw "That folder does not appear to be a Kenshi installation: $enteredPath"
        }
        $KenshiPath = (Resolve-Path -LiteralPath $enteredPath).Path
    }
}

$runningKenshi = Get-Process -Name "kenshi", "kenshi_x64" -ErrorAction SilentlyContinue
if ($runningKenshi) {
    throw "Kenshi is running. Close the game and launcher, then run this installer again."
}

$modsPath = Join-Path $KenshiPath "mods"
if (-not (Test-Path -LiteralPath $modsPath -PathType Container)) {
    New-Item -ItemType Directory -Path $modsPath | Out-Null
}

$targetPath = Join-Path $modsPath $modName
$fullScriptRoot = [IO.Path]::GetFullPath($scriptRoot).TrimEnd('\')
$fullTargetPath = [IO.Path]::GetFullPath($targetPath).TrimEnd('\')
if (
    $fullScriptRoot.Equals($fullTargetPath, [StringComparison]::OrdinalIgnoreCase) -or
    $fullScriptRoot.StartsWith("$fullTargetPath\", [StringComparison]::OrdinalIgnoreCase)
) {
    throw "Extract the downloaded branch somewhere outside Kenshi's mods folder, then run the installer again."
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = Join-Path $modsPath "$modName.backup-$timestamp"
$failedPath = Join-Path $modsPath "$modName.failed-$timestamp"
$backupCreated = $false

Write-Host "Kenshi installation: $KenshiPath"
if (Test-Path -LiteralPath $targetPath) {
    Write-Host "Backing up the existing mod to: $backupPath"
    Move-Item -LiteralPath $targetPath -Destination $backupPath
    $backupCreated = $true
}

try {
    New-Item -ItemType Directory -Path $targetPath | Out-Null

    foreach ($file in $requiredFiles) {
        $source = Join-Path $scriptRoot $file
        $destination = Join-Path $targetPath $file
        Copy-Item -LiteralPath $source -Destination $destination

        $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        $destinationHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
        if ($sourceHash -ne $destinationHash) {
            throw "Verification failed after copying $file"
        }
    }
}
catch {
    if (Test-Path -LiteralPath $targetPath) {
        Move-Item -LiteralPath $targetPath -Destination $failedPath
    }
    if ($backupCreated -and (Test-Path -LiteralPath $backupPath)) {
        Move-Item -LiteralPath $backupPath -Destination $targetPath
        Write-Host "The previous mod folder was restored." -ForegroundColor Yellow
    }
    throw
}

Write-Host ""
Write-Host "Installation completed successfully." -ForegroundColor Green
Write-Host "Installed to: $targetPath"
if ($backupCreated) {
    Write-Host "Previous version: $backupPath"
}
Write-Host ""
Write-Host "Start Kenshi and confirm '$modName' appears in the Mods tab."
Write-Host "For the world-building deletions, test with a new game first; an old save may retain spawned buildings."
