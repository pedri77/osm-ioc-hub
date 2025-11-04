#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs -d '\n' -I {} echo {}) || true
fi

python -c "import client_osm as c; 
import os
terms=[t.strip() for t in os.getenv('HARVEST_TERMS','crypto').split(',') if t.strip()]
eco=os.getenv('HARVEST_ECOSYSTEM')
total=0
for t in terms:
    n=c.harvest(t, ecosystem=eco)
    print(f'[HARVEST] {t}: {n} IOCs')
    total+=n
print('[HARVEST] TOTAL:', total)
"
