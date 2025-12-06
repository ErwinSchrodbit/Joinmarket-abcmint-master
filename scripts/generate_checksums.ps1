param(
  [string]$DistPath = "dist",
  [string]$Pattern = "*.exe"
)
$files = Get-ChildItem -Path $DistPath -Filter $Pattern -File
if (-not $files) {
  Write-Error "No matching files in $DistPath"
  exit 1
}
$out = Join-Path $DistPath "SHA256SUMS.txt"
$lines = @()
foreach ($f in $files) {
  $h = Get-FileHash -Algorithm SHA256 -Path $f.FullName
  $name = Split-Path -Leaf $f.FullName
  $lines += ("{0}  {1}" -f $h.Hash, $name)
}
Set-Content -Path $out -Value ($lines -join "`n") -NoNewline
Write-Host ("Wrote {0}" -f $out)
