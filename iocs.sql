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
