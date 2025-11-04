\
Param(
  [string]$RepoPath = ".",
  [string]$PythonExe = "python"
)

Set-Location $RepoPath

# Carga variables del .env si existe
if (Test-Path ".env") {
  Get-Content .env | ForEach-Object {
    if ($_ -and ($_ -notmatch '^#')) {
      $name, $value = $_.Split('=',2)
      [System.Environment]::SetEnvironmentVariable($name, $value)
    }
  }
}

# Ejecuta ingesta
$code = @"
import os
import client_osm as c
terms = [t.strip() for t in os.getenv('HARVEST_TERMS','crypto').split(',') if t.strip()]
eco   = os.getenv('HARVEST_ECOSYSTEM')
tot=0
for t in terms:
    n=c.harvest(t, ecosystem=eco)
    print(f'[HARVEST] {t}: {n}')
    tot+=n
print('[HARVEST] TOTAL:', tot)
"@
& $PythonExe -c $code
