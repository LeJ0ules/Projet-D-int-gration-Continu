# TP CI/CD – pipeline data

Pipeline CSV → S3 → PostgreSQL, avec CI GitHub Actions et déploiement Kubernetes.

## Lancer en local
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ruff check .
pytest tests/unit
```



docker run -d \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=pipeline \
  -p 5433:5432 \
  postgres:16

export DATABASE_URL=postgresql://postgres:test@localhost:5433/pipeline
python3 -m src.pipeline
python3 -m src.pipeline



test integration : 
pytest tests/integration