FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Couche dépendances séparée : le cache Docker n'est invalidé que si
# requirements.txt change, pas à chaque modification du code.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY app.py .

# Exécution sans privilèges
RUN useradd --create-home --uid 1000 copilote \
    && mkdir -p /app/chroma_db /app/data \
    && chown -R copilote:copilote /app
USER copilote

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
