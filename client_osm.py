import os, json, sqlite3, requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("OSM_API_BASE", "https://opensourcemalware.com").rstrip("/")
API_KEY  = os.getenv("OSM_API_KEY")
HEADERS  = {"Accept": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

DB_PATH  = os.getenv("DB_PATH", "iocs.db")

def _get(path, params=None):
    url = f"{BASE_URL}{path}"
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

# Ajusta estas rutas según la documentación pública de OSM:
SEARCH_PATH   = "/api/search"                 # p.ej. búsqueda de artifacts
ART_IOCS_PATH = "/api/artifacts/{id}/iocs"    # IOCs por artifact

def search_artifacts(q: str, ecosystem: str|None=None):
    params = {"q": q}
    if ecosystem: params["ecosystem"] = ecosystem
    return _get(SEARCH_PATH, params=params)

def list_iocs(artifact_id: str):
    return _get(ART_IOCS_PATH.format(id=artifact_id))

def ensure_db(db=DB_PATH):
    con = sqlite3.connect(db)
    cur = con.cursor()
    with open("iocs.sql","r",encoding="utf-8") as f:
        cur.executescript(f.read())
    con.commit()
    con.close()

def normalize_ioc(raw, source="OpenSourceMalware", artifact=None, ecosystem=None):
    return {
        "value": raw.get("value") or raw.get("indicator"),
        "type":  (raw.get("type") or "").lower(),
        "first_seen": raw.get("first_seen"),
        "last_seen": raw.get("last_seen"),
        "confidence": raw.get("confidence", 70),
        "source": source,
        "artifact": artifact,
        "ecosystem": ecosystem,
        "tags": json.dumps(raw.get("tags", []), ensure_ascii=False)
    }

def upsert_iocs(rows, db=DB_PATH):
    if not rows: return 0
    con = sqlite3.connect(db)
    cur = con.cursor()
    for r in rows:
        cur.execute("""            INSERT INTO iocs(value,type,first_seen,last_seen,confidence,source,artifact,ecosystem,tags)
            VALUES (:value,:type,:first_seen,:last_seen,:confidence,:source,:artifact,:ecosystem,:tags)
            ON CONFLICT(value,type,source) DO UPDATE SET
              last_seen=COALESCE(excluded.last_seen, iocs.last_seen),
              confidence=MAX(iocs.confidence, excluded.confidence),
              tags=CASE WHEN excluded.tags!='[]' AND excluded.tags IS NOT NULL THEN excluded.tags ELSE iocs.tags END
        """, r)
    con.commit()
    con.close()
    return len(rows)

def harvest(query: str, ecosystem: str|None=None, db=DB_PATH):
    ensure_db(db)
    artifacts = search_artifacts(query, ecosystem)
    harvested = 0
    for a in artifacts.get("items", []):
        aid   = a.get("id") or a.get("artifact_id") or a.get("name")
        ecos  = a.get("ecosystem") or ecosystem
        iocs  = list_iocs(aid)
        items = iocs.get("items", iocs)
        rows  = [normalize_ioc(i, artifact=aid, ecosystem=ecos) for i in items]
        harvested += upsert_iocs(rows, db=db)
    return harvested

if __name__ == "__main__":
    terms = [t.strip() for t in os.getenv("HARVEST_TERMS","crypto").split(",") if t.strip()]
    eco   = os.getenv("HARVEST_ECOSYSTEM")
    total = 0
    for t in terms:
        n = harvest(t, ecosystem=eco)
        print(f"[OK] {t}: {n} IOCs")
        total += n
    print(f"TOTAL: {total}")
