from app import q
import misp_client as misp
from datetime import datetime, timezone
import sys

def main(artifact=None, limit=2000):
    sql = "SELECT * FROM iocs WHERE 1=1"
    params = []
    if artifact:
        sql += " AND artifact LIKE ?"; params.append(f"%{artifact}%")
    sql += " ORDER BY COALESCE(last_seen, first_seen) DESC LIMIT ?"; params.append(limit)
    rows = q(sql, params)
    if not rows:
        print("No hay IOCs para enviar"); return
    attrs = misp.build_attributes(rows)
    title = f"OpenSourceMalware IOCs ({artifact or 'all'}) – {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}"
    resp = misp.create_event(title, attrs)
    print(f"Enviados {len(attrs)} atributos a MISP")
    print(resp)

if __name__ == "__main__":
    art = sys.argv[1] if len(sys.argv)>1 else None
    main(artifact=art)
