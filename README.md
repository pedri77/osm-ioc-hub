# OpenSourceMalware IOC Hub

Ingesta y normalización de IOCs desde **OpenSourceMalware** (OSM), con:
- 🧲 **ETL** a SQLite (evita duplicados por `(value,type,source)`).
- 🌐 **API FastAPI**: `/iocs`, `/export/csv`, `/export/stix`, `/export/misp`, `POST /push/misp`.
- 🖥️ **UI Streamlit** para consulta ad-hoc.
- 🐳 **Docker Compose** para despliegue rápido.
- 🔌 **Conector MISP** para publicar atributos automáticamente.
- 🛡️ **Reverse proxy** con **Basic Auth** mediante Caddy.

> ⚠️ Ajusta los endpoints si cambian en la documentación pública de OSM. El cliente deja rutas centralizadas para editar con mínimo esfuerzo.

## Requisitos

- Python 3.10+
- (Opcional) Docker y Docker Compose
- Variables de entorno (`.env`):
  - `OSM_API_BASE=https://opensourcemalware.com`
  - `OSM_API_KEY=` (si la API requiere token)
  - `HARVEST_TERMS=crypto,auth,token,ai,webdriver`
  - `HARVEST_ECOSYSTEM=npm`
  - `MISP_URL=https://misp.ejemplo.local`
  - `MISP_API_KEY=changeme`
  - `MISP_VERIFY_SSL=true`
  - `MISP_PUBLISH=true`
  - `BASIC_AUTH_USER=analyst`
  - `BASIC_AUTH_HASH=$2a$14$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

Copia `.env.example` a `.env` y ajusta valores.

## Instalación (desarrollo local)

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# inicializa DB e ingesta de ejemplo
python client_osm.py

# lanza API
uvicorn app:app --reload

# UI (en otra terminal)
streamlit run ui.py
```

- API: http://127.0.0.1:8000/docs
- UI:  http://127.0.0.1:8501

## Endpoints principales

- `GET /iocs?artifact=&since=&limit=` — consulta IOCs normalizados.
- `GET /export/csv` — CSV completo.
- `GET /export/stix` — Bundle STIX 2.1 (indicator + observed-data + relationship).
- `GET /export/misp` — Evento MISP con atributos.
- `POST /push/misp?artifact=&limit=` — envía atributos a MISP.

## Ingesta programada

### Linux (cron)
Edita `scripts/cron_harvest.sh` y añade al crontab:
```
*/30 * * * * /bin/bash /ruta/osm-ioc-hub/scripts/cron_harvest.sh >> /var/log/osm_harvest.log 2>&1
```

### Windows (Task Scheduler)
Ejecuta (PowerShell) `scripts/windows_task_harvest.ps1` como acción programada.

## Docker

```bash
docker compose up --build
```

- API → `http://localhost:8000` (directo) o `http://localhost:8080/api` (proxy Caddy)
- UI  → `http://localhost:8501` (directo) o `http://localhost:8080/ui`  (proxy Caddy)
- Volumen `./data` persistirá `iocs.db`.

## Esquema SQLite

```sql
-- iocs.sql
CREATE TABLE IF NOT EXISTS iocs (
  id INTEGER PRIMARY KEY,
  value TEXT NOT NULL,
  type TEXT CHECK(type IN ('ip','domain','url','hash','email','c2','asn')),
  first_seen TEXT,
  last_seen TEXT,
  confidence INTEGER,
  source TEXT,
  artifact TEXT,
  ecosystem TEXT,
  tags TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_ioc ON iocs(value, type, source);
CREATE INDEX IF NOT EXISTS ix_last_seen ON iocs(last_seen);
```

## Integración con MISP

1) Configura variables en `.env`:
```
MISP_URL=https://misp.ejemplo.local
MISP_API_KEY=xxxxxxxxxxxxxxxxx
MISP_VERIFY_SSL=true
MISP_PUBLISH=true
```

2) Envía IOCs a MISP:
- Vía API: `POST http://localhost:8080/api/push/misp?artifact=npm`
- Vía CLI: `python scripts/push_misp.py [artifact]`

> Los atributos se mapean por tipo (ip→ip-dst, domain→domain, url→url, hash→md5, …).

## STIX 2.1 mejorado

`GET /export/stix` devuelve un **Bundle** con:
- `indicator` por IOC (pattern según tipo)
- `observed-data` correspondiente
- relación `based-on` entre `indicator` → `observed-data`

Los IDs se generan de forma **determinista** para asegurar *de-dup* entre exportaciones.

## Reverse proxy (Basic Auth)

Levanta el proxy:
```
docker compose up --build
```

- API: `http://localhost:8080/api`
- UI:  `http://localhost:8080/ui`

**Credenciales:** usuario = `${BASIC_AUTH_USER}` y contraseña según el hash `${BASIC_AUTH_HASH}`.

Para crear el hash:
```
docker run --rm caddy:2.8 caddy hash-password --plaintext "TuPasswordFuerte"
```
Copia el hash en `.env`.

## Licencia

MIT
