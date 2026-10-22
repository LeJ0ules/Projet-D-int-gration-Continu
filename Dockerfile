FROM python:3.12-slim

WORKDIR /app

# On copie requirements.txt d'abord : Docker met cette couche en cache
# tant que les dépendances ne changent pas (builds plus rapides).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python", "-m", "src.pipeline"]
