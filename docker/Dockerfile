FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
ENV PYTHONUNBUFFERED=1

# Crea carpeta de datos
RUN mkdir -p /app/data && touch /app/data/iocs.db
ENV DB_PATH=/app/data/iocs.db

# Inicializa DB (no falla si no hay datos)
RUN python -c "import client_osm as c; c.ensure_db()"

EXPOSE 8000 8501
CMD sh -c "uvicorn app:app --host 0.0.0.0 --port 8000 & streamlit run ui.py --server.address 0.0.0.0 --server.port 8501 && wait"
