from fastapi import FastAPI, Response, Query
import sqlite3, csv, io, json, uuid
from datetime import datetime, timezone
import misp_client as misp

app = FastAPI(title="OSM IOC Hub", version="0.2.0")

def q(sql, params=()):
    con = sqlite3.connect("iocs.db")
    con.row_factory = sqlite3.Row
    rows = con.execute(sql, params).fetchall()
    con.close()
    return [dict(r) for r in rows]

@app.get("/iocs")
def get_iocs(artifact: str|None=None, since: str|None=None, limit: int=500):
    sql = "SELECT * FROM iocs WHERE 1=1"
    params = []
    if artifact:
        sql += " AND artifact LIKE ?"; params.append(f"%{artifact}%")
    if since:
        sql += " AND (COALESCE(last_seen,first_seen) >= ?)"
        params.append(since)
    sql += " ORDER BY COALESCE(last_seen, first_seen) DESC LIMIT ?"; params.append(limit)
    return {"items": q(sql, params)}

@app.get("/export/csv")
def export_csv():
    rows = q("SELECT * FROM iocs ORDER BY COALESCE(last_seen, first_seen) DESC")
    if not rows:
        return Response("", media_type="text/csv",
                        headers={"Content-Disposition":"attachment; filename=iocs.csv"})
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return Response(content=output.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition":"attachment; filename=iocs.csv"})

# ---------- STIX 2.1 MEJORADO ----------
def _uuid_ns(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))

def _stix_object_for_ioc(r: dict):
    v = r["value"]; t = (r["type"] or "").lower()
    base = f"{t}:{v}"
    id_indicator = f"indicator--{_uuid_ns('indicator:'+base)}"
    id_observed  = f"observed-data--{_uuid_ns('observed:'+base)}"

    pattern = {
        "ip":    f"[ipv4-addr:value = '{v}']",
        "domain":f"[domain-name:value = '{v}']",
        "url":   f"[url:value = '{v}']",
        "hash":  f"[file:hashes.MD5 = '{v}']",
        "email": f"[email-addr:value = '{v}']",
        "asn":   f"[autonomous-system:number = '{v}']",
        "c2":    f"[domain-name:value = '{v}']"
    }.get(t, f"[x-open:value = '{v}']")

    indicator = {
        "type":"indicator", "spec_version":"2.1", "id": id_indicator,
        "name": base, "created":"2025-01-01T00:00:00Z", "modified":"2025-01-01T00:00:00Z",
        "pattern": pattern, "pattern_type":"stix",
        "valid_from": (r.get("first_seen") or "2025-01-01T00:00:00Z"),
        "labels":[r.get("ecosystem") or "open-source", "OpenSourceMalware"],
        "confidence": r.get("confidence") or 50,
        "x_open_source": r.get("source")
    }

    obj_id = "0"
    objs = {}
    if t == "ip":
        objs[obj_id] = {"type":"ipv4-addr", "value": v}
    elif t in ("domain","c2"):
        objs[obj_id] = {"type":"domain-name", "value": v}
    elif t == "url":
        objs[obj_id] = {"type":"url", "value": v}
    elif t == "hash":
        objs[obj_id] = {"type":"file", "hashes": {"MD5": v}}
    elif t == "email":
        objs[obj_id] = {"type":"email-addr", "value": v}
    elif t == "asn":
        objs[obj_id] = {"type":"autonomous-system", "number": v}
    else:
        objs[obj_id] = {"type":"x-open", "value": v}

    observed = {
        "type":"observed-data", "spec_version":"2.1", "id": id_observed,
        "first_observed": (r.get("first_seen") or "2025-01-01T00:00:00Z"),
        "last_observed": (r.get("last_seen") or r.get("first_seen") or "2025-01-01T00:00:00Z"),
        "number_observed": 1,
        "objects": objs
    }

    relation = {
        "type":"relationship", "spec_version":"2.1",
        "id": f"relationship--{_uuid_ns('rel:'+base)}",
        "relationship_type":"based-on",
        "source_ref": id_indicator,
        "target_ref": id_observed
    }

    return indicator, observed, relation

@app.get("/export/stix")
def export_stix():
    rows = q("SELECT * FROM iocs")
    objs = []
    for r in rows:
        indicator, observed, relation = _stix_object_for_ioc(r)
        objs.extend([indicator, observed, relation])
    bundle = {"type":"bundle","id":"bundle--00000000-0000-4000-8000-000000000000","objects":objs}
    return bundle
# ---------- FIN STIX 2.1 MEJORADO ----------

# ---------- PUSH A MISP ----------
@app.post("/push/misp")
def push_misp(artifact: str | None = Query(default=None), limit: int = 2000):
    sql = "SELECT * FROM iocs WHERE 1=1"
    params = []
    if artifact:
        sql += " AND artifact LIKE ?"; params.append(f"%{artifact}%")
    sql += " ORDER BY COALESCE(last_seen, first_seen) DESC LIMIT ?"; params.append(limit)
    rows = q(sql, params)

    if not rows:
        return {"status":"empty", "sent":0}

    attrs = misp.build_attributes(rows)
    title = f"OpenSourceMalware IOCs ({artifact or 'all'}) – {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}"
    resp = misp.create_event(title, attrs)
    return {"status":"ok", "sent": len(attrs), "misp_response": resp}
# ---------- FIN PUSH A MISP ----------
