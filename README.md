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


ruff check . && pytest tests/unit
test integration : 
pytest tests/integration
pytest tests/integration/test_retry.py -v --log-cli-level=WARNING



lancement seaweed :
  echo '{"identities":[{"name":"dev","credentials":[{"accessKey":"testkey","secretKey":"testsecret"}],"actions":["Admin","Read","Write","List","Tagging"]}]}' > s3config.json
  docker run -d --name seaweedfs -p 8333:8333 -v "$PWD/s3config.json:/etc/seaweedfs/s3config.json:ro" chrislusf/seaweedfs:latest mini -dir=/data -s3.config=/etc/seaweedfs/s3config.json -bucket=transactions
  export S3_ENDPOINT_URL=http://localhost:8333 S3_ACCESS_KEY=testkey S3_SECRET_KEY=testsecret