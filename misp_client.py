import os, requests, json
from typing import List, Dict

MISP_URL       = os.getenv("MISP_URL", "").rstrip("/")
MISP_API_KEY   = os.getenv("MISP_API_KEY", "")
MISP_VERIFY_SSL= os.getenv("MISP_VERIFY_SSL", "true").lower() == "true"
MISP_PUBLISH   = os.getenv("MISP_PUBLISH", "true").lower() == "true"

HEADERS = {
    "Authorization": MISP_API_KEY,
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def _check():
    if not MISP_URL or not MISP_API_KEY:
        raise RuntimeError("Config MISP incompleta: MISP_URL / MISP_API_KEY")

def _map_type(t: str) -> str:
    return {
        "ip":"ip-dst",
        "domain":"domain",
        "url":"url",
        "hash":"md5",
        "email":"email-dst",
        "c2":"domain",
        "asn":"AS"
    }.get(t, "text")

def create_event(title: str, attributes: List[Dict]) -> Dict:
    _check()
    body = {"Event":{"info": title, "published": bool(MISP_PUBLISH), "Attribute": attributes}}
    r = requests.post(f"{MISP_URL}/events/add", headers=HEADERS,
                      data=json.dumps(body), verify=MISP_VERIFY_SSL, timeout=60)
    r.raise_for_status()
    return r.json()

def build_attributes(rows: List[Dict]) -> List[Dict]:
    attrs = []
    for r in rows:
        attrs.append({
            "type": _map_type((r.get("type") or "").lower()),
            "value": r["value"],
            "category": "Network activity",
            "to_ids": True,
            "comment": f"source={r.get('source')} artifact={r.get('artifact')} ecosystem={r.get('ecosystem')}"
        })
    return attrs
