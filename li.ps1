<#
LinkedIn public job search (guest endpoints, no login, no install). Windows PowerShell 5.1+.

Search (prints: id | title | company | location | posted date):
  .\li.ps1 -Keywords "revenue operations" -Location "Porto, Portugal" -Days 21
  .\li.ps1 -Keywords "GTM engineer" -Location "European Union" -Remote

Fetch full descriptions to files (one .txt per id):
  .\li.ps1 -Detail -Ids 4370672271,4413028604 -OutDir "$env:TEMP\lij"
#>
param(
  [string]$Keywords,
  [string]$Location,
  [int]$Days = 21,
  [switch]$Remote,
  [int]$Pages = 2,
  [switch]$Detail,
  [string[]]$Ids,
  [string]$OutDir = "$env:TEMP\lij"
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Web
$ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
$base = 'https://www.linkedin.com/jobs-guest/jobs/api'

function Get-Html($url) {
  for ($try = 1; $try -le 3; $try++) {
    try { return (Invoke-WebRequest -Uri $url -UserAgent $ua -UseBasicParsing).Content }
    catch {
      $code = $_.Exception.Response.StatusCode.value__
      if ($code -eq 404) { return $null }
      if ($try -eq 3) { throw }
      Start-Sleep -Seconds (5 * $try)   # back off on 429 / transient errors
    }
  }
}
function Clean($s) {
  if (-not $s) { return '' }
  ([System.Web.HttpUtility]::HtmlDecode(($s -replace '<[^>]+>', ' '))) -replace '\s+', ' ' | ForEach-Object { $_.Trim() }
}
function Grab($html, $pattern) { Clean ([regex]::Match($html, $pattern).Groups[1].Value) }

if (-not $Detail) {
  if (-not $Keywords) { throw 'Pass -Keywords (and usually -Location).' }
  $q = "keywords=$([uri]::EscapeDataString($Keywords))&location=$([uri]::EscapeDataString($Location))&f_TPR=r$($Days*86400)&sortBy=DD"
  if ($Remote) { $q += '&f_WT=2' }
  $seen = @{}
  for ($p = 0; $p -lt $Pages; $p++) {
    $html = Get-Html "$base/seeMoreJobPostings/search?$q&start=$($p*10)"
    if (-not $html) { break }
    # Each job card is an <li>; parse fields per card so one odd card cannot corrupt the next
    $cards = $html -split '<li>' | Where-Object { $_ -match 'jobPosting:(\d+)' }
    if (-not $cards) { break }
    foreach ($c in $cards) {
      $id = [regex]::Match($c, 'jobPosting:(\d+)').Groups[1].Value
      if ($seen[$id]) { continue }; $seen[$id] = 1
      $title = Grab $c '(?s)base-search-card__title[^>]*>(.*?)</h3>'
      $co    = Grab $c '(?s)base-search-card__subtitle[^>]*>(.*?)</h4>'
      $loc   = Grab $c '(?s)job-search-card__location[^>]*>(.*?)</span>'
      $date  = [regex]::Match($c, 'datetime="([^"]+)"').Groups[1].Value
      "$id | $title | $co | $loc | $date"
    }
    Start-Sleep -Milliseconds 1200
  }
}
else {
  New-Item -ItemType Directory -Force $OutDir | Out-Null
  foreach ($id in $Ids) {
    try {
      $html = Get-Html "$base/jobPosting/$id"
      if (-not $html) { "$id NOT FOUND (closed or removed)"; continue }
      $title = Grab $html '(?s)top-card-layout__title[^>]*>(.*?)</h2>'
      $co    = Grab $html '(?s)topcard__org-name-link[^>]*>(.*?)</a>'
      $loc   = Grab $html '(?s)topcard__flavor--bullet[^>]*>(.*?)</span>'
      $crit  = [regex]::Matches($html, '(?s)description__job-criteria-subheader[^>]*>(.*?)</h3>\s*<span[^>]*>(.*?)</span>') |
               ForEach-Object { "$(Clean $_.Groups[1].Value): $(Clean $_.Groups[2].Value)" }
      $desc  = [regex]::Match($html, '(?s)show-more-less-html__markup[^>]*>(.*?)</div>').Groups[1].Value
      $desc  = $desc -replace '<br\s*/?>', "`n" -replace '</(p|li|ul|ol|h\d)>', "`n" -replace '<li>', '- ' -replace '<[^>]+>', ''
      $desc  = ([System.Web.HttpUtility]::HtmlDecode($desc)) -replace "(`r?`n\s*){3,}", "`n`n"
      $text  = "### $title | $co | $loc`n$($crit -join ' / ')`nhttps://www.linkedin.com/jobs/view/$id`n`n$desc"
      $file  = Join-Path $OutDir "$id.txt"
      $text | Out-File -Encoding utf8 $file
      "$id ok $((Get-Item $file).Length) bytes | $title | $co"
    } catch { "$id ERR $($_.Exception.Message)" }
    Start-Sleep -Milliseconds 1200
  }
}
