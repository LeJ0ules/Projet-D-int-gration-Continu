# TP CI/CD – pipeline data

Pipeline CSV → S3 → PostgreSQL, avec CI GitHub Actions et déploiement Kubernetes.

## Lancer en local
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ruff check .
pytest tests/unit
```
