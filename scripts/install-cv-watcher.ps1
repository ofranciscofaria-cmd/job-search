<#
One-time setup for the CV watcher (Windows PowerShell 5.1+, no admin, no Python).

What it does from then on, in the background, every time Windows starts:
  a file downloaded as   "<Company> - CV - Francisco Faria.pdf"   (the name the builder gives the Notion CV PDF)
  is moved from Downloads to   Job Search\CVs\<Company>\CV - Francisco Faria.pdf
  If that folder already has a CV (a revised version), the older one goes to Job Search\CVs\<Company>\old\.

How to install: copy this whole file, paste it into a PowerShell window, press Enter.
How to remove: delete "CV watcher" from the Startup folder (Win+R, type shell:startup) and restart.
Log: Job Search\CVs\watcher.log
#>

$ErrorActionPreference = 'Stop'

# Job Search folder (his OneDrive copy), else Documents\Job Search
$jobSearch = Join-Path $env:USERPROFILE 'OneDrive\Documentos\Job Search'
if (-not (Test-Path -LiteralPath $jobSearch)) {
    $jobSearch = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Job Search'
}
$cvRoot = Join-Path $jobSearch 'CVs'
New-Item -ItemType Directory -Force -Path $cvRoot | Out-Null

$watcherPath = Join-Path $jobSearch 'cv-watcher.ps1'
$watcher = @'
param([Parameter(Mandatory = $true)][string]$Root)

# Only one copy runs at a time
$created = $false
$mutex = New-Object System.Threading.Mutex($true, 'Local\FranciscoCvWatcher', [ref]$created)
if (-not $created) { exit }

$downloads = $null
try { $downloads = (New-Object -ComObject Shell.Application).NameSpace('shell:Downloads').Self.Path } catch { }
if (-not $downloads -or -not (Test-Path -LiteralPath $downloads)) { $downloads = Join-Path $env:USERPROFILE 'Downloads' }

$log = Join-Path $Root 'watcher.log'
$pattern = '^(?<co>.+?) - CV - Francisco Faria(?: ?\(\d+\))?\.pdf$'
$invalid = [IO.Path]::GetInvalidFileNameChars()

function Write-Log([string]$msg) {
    Add-Content -LiteralPath $log -Value ((Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + '  ' + $msg)
}

Write-Log "Started. Watching $downloads"

while ($true) {
    $files = Get-ChildItem -LiteralPath $downloads -Filter '* - CV - Francisco Faria*.pdf' -File -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        if ($f.Name -notmatch $pattern) { continue }
        $company = $Matches['co'].Trim()
        foreach ($c in $invalid) { $company = $company.Replace([string]$c, '') }
        if (-not $company) { continue }

        # Skip while the browser is still writing the file
        try { $s = [IO.File]::Open($f.FullName, 'Open', 'ReadWrite', 'None'); $s.Close() } catch { continue }

        try {
            $dir = Join-Path $Root $company
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
            $dest = Join-Path $dir 'CV - Francisco Faria.pdf'
            if (Test-Path -LiteralPath $dest) {
                $oldDir = Join-Path $dir 'old'
                New-Item -ItemType Directory -Force -Path $oldDir | Out-Null
                $stamp = (Get-Item -LiteralPath $dest).LastWriteTime.ToString('yyyy-MM-dd HHmm')
                Move-Item -LiteralPath $dest -Destination (Join-Path $oldDir "CV - Francisco Faria ($stamp).pdf") -Force
            }
            Move-Item -LiteralPath $f.FullName -Destination $dest -Force
            Write-Log "$($f.Name) -> $dest"
        } catch {
            Write-Log "FAILED $($f.Name): $($_.Exception.Message)"
        }
    }
    Start-Sleep -Seconds 3
}
'@
Set-Content -LiteralPath $watcherPath -Value $watcher -Encoding UTF8

# Start with Windows: shortcut in the Startup folder, hidden window
$ps = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$watcherPath`" -Root `"$cvRoot`""
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) 'CV watcher.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $ps
$shortcut.Arguments = $arguments
$shortcut.WindowStyle = 7
$shortcut.Save()

# Start it now too
Start-Process -FilePath $ps -ArgumentList $arguments -WindowStyle Hidden

Write-Host ''
Write-Host "CV watcher installed and running."
Write-Host "CVs will be saved in: $cvRoot"
Write-Host "Test: save any PDF in Downloads as 'Test - CV - Francisco Faria.pdf'; within a few seconds it moves to $cvRoot\Test\"
