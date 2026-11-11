# TP Intégration & Déploiement continus – pipeline data

Pipeline de transactions financières : des fichiers CSV sont déposés dans un S3, traités
(sommes par IBAN et par banque, détection des montants > 5000 €), puis insérés dans
PostgreSQL. La qualité est vérifiée par une CI (GitHub Actions) et le déploiement est
automatisé sur Kubernetes par une CD.

## Architecture

```mermaid
flowchart LR
    G[generate.py<br/>CSV déterministes] -->|upload| S3[(S3 local<br/>SeaweedFS<br/>incoming/*.csv)]
    S3 -->|download + retry| P[pipeline.py]
    P -->|SHA-256 déjà vu ?| DB[(PostgreSQL)]
    P -->|transforms.py<br/>fonctions pures| P
    P -->|insertion atomique<br/>+ retry| DB
```

## Structure du dépôt

| Chemin | Rôle |
|---|---|
| `src/generate.py` | Génère des CSV **non aléatoires** (cas limites : 5000.00, 5000.01, 4999.99) |
| `src/models.py` | `Transaction` typée et immuable (`datetime`, `Decimal`) |
| `src/loaders.py` | Lecture / parsing des CSV, hash SHA-256 du contenu |
| `src/transforms.py` | Traitements : **fonctions pures**, sans accès fichier, réseau ni base |
| `src/schema.sql`, `src/db.py` | Schéma relationnel, insertion atomique, retry |
| `src/s3.py` | Accès S3 (boto3) avec retry |
| `src/pipeline.py` | Orchestration, 3 modes : `all`, `seed`, `process` |
| `tests/unit/` | Tests unitaires (sans service externe) |
| `tests/integration/` | Tests sur vraie base PostgreSQL et vrai S3 |
| `k8s/` | Manifests Kubernetes (PostgreSQL, SeaweedFS, CronJob) |
| `.github/workflows/ci.yml` | CI : lint, tests unitaires, pipeline, tests d'intégration, build Docker |
| `.github/workflows/cd.yml` | CD : déploiement sur un cluster kind éphémère, vérification, publication |
| `infra/` | OpenTofu : infrastructure cloud (Kubernetes managé, PostgreSQL managé, S3) sur Scaleway |
| `.github/workflows/infra.yml` | Vérifie la configuration OpenTofu (format, validation) |

## Format des données

CSV avec les champs du sujet, plus `montant_eur` (nécessaire aux traitements) :

`datetime_transaction, iban_origine, pays_source, banque_source, iban_destinataire, pays_destinataire, montant_eur`

Les IBAN sont fictifs.

## Base de données

- `processed_files` : registre des fichiers traités, clé primaire = hash SHA-256 du contenu.
- `transactions` : une ligne par transaction, avec le flag `flagged` (montant **strictement** > 5000).
- `sum_sent_by_iban`, `sum_sent_by_bank`, `sum_received_by_iban` : agrégats par fichier.

Les montants sont en `NUMERIC(14,2)` côté base et en `Decimal` côté Python (jamais de `float`).

## Lancer en local

Prérequis : Python 3.12, Docker.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ruff check . && pytest tests/unit

# Services (PostgreSQL + S3 local)
docker run -d --name pg -e POSTGRES_PASSWORD=test -e POSTGRES_DB=pipeline -p 5432:5432 postgres:16
echo '{"identities":[{"name":"dev","credentials":[{"accessKey":"testkey","secretKey":"testsecret"}],"actions":["Admin","Read","Write","List","Tagging"]}]}' > s3config.json
docker run -d --name seaweedfs -p 8333:8333 \
  -v "$PWD/s3config.json:/etc/seaweedfs/s3config.json:ro" \
  chrislusf/seaweedfs:4.53 \
  mini -dir=/data -s3.config=/etc/seaweedfs/s3config.json -bucket=transactions

export DATABASE_URL=postgresql://postgres:test@localhost:5432/pipeline
export S3_ENDPOINT_URL=http://localhost:8333 S3_ACCESS_KEY=testkey S3_SECRET_KEY=testsecret

python -m src.pipeline          # génère, dépose dans S3, traite, insère
python -m src.pipeline          # 2e lancement : tous les fichiers sont ignorés
pytest tests/integration        # vérifie les valeurs en base
```

Sans ces variables d'environnement, les tests d'intégration sont ignorés en local ; en CI
(variable `CI` définie), leur absence est une **erreur**, pour qu'une CI verte ne cache
jamais des tests non exécutés.

## Choix de conception

**Éviter de traiter deux fois un fichier.** Un fichier est identifié par le hash SHA-256 de
son *contenu* (pas son nom). Le pipeline vérifie le hash avant traitement, et la clé primaire
de `processed_files` est un garde-fou : même avec deux exécutions simultanées, la seconde
insertion est refusée.

**Insertion atomique.** Fichier, transactions et agrégats sont insérés dans une seule
transaction SQL : tout est enregistré, ou rien. Un fichier n'est donc jamais « à moitié »
traité, et un échec peut être rejoué sans nettoyage.

**Retry ciblé (tenacity).** On ne réessaie que les erreurs transitoires : connexion
PostgreSQL coupée, erreurs réseau S3 et réponses 5xx. Les erreurs définitives (fichier
inexistant, fichier déjà traité) ne sont pas réessayées. Attente exponentielle, nouvelle
connexion à chaque essai. Cas testé : l'insertion réussit mais la réponse se perd ; le retry
retombe sur un fichier déjà enregistré et l'ignore, sans doublon.

**Séparation I/O et traitement.** `transforms.py` ne contient que des fonctions pures
(entrées → sorties, aucune modification des arguments) ; elles se testent sans service.
Les chargements (`loaders.py`, `s3.py`, `db.py`) sont isolés.

**Données de test déterministes.** Les totaux attendus sont connus à l'avance et calculés à
la main dans les tests, ce qui permet de détecter un bug de traitement. Un `>=` à la place de
`>` fait échouer la CI (scénario de l'étape 6 : voir la branche `bug/flag-seuil`).

**Choix du S3 local : SeaweedFS.** MinIO Community Edition n'est plus distribué ni maintenu
comme avant (plus d'images officielles) ; SeaweedFS est l'une des alternatives citées par le
sujet et tient dans un seul conteneur. Le code ne dépend pas du fournisseur : seule l'URL du
endpoint (`S3_ENDPOINT_URL`) change.

## CI (`ci.yml`)

À chaque push et pull request : lint (ruff), tests unitaires, démarrage de PostgreSQL
(service GitHub) et de SeaweedFS (`docker run`), exécution de la pipeline, tests
d'intégration, build de l'image Docker.

## CD (`cd.yml`)

Déclenchée quand la CI est verte sur `main` (ou manuellement) :

1. build de l'image et chargement dans un cluster **kind éphémère** ;
2. création des Secrets avec des identifiants **aléatoires** (rien dans le dépôt) ;
3. `kubectl apply -k k8s/` : PostgreSQL et SeaweedFS (StatefulSet + volume), CronJob ;
4. job `seed` qui dépose des fichiers dans S3 ;
5. exécution du CronJob **deux fois** : 12 transactions en base la 1re fois, rien de
   retraité la 2e ;
6. si tout est vérifié, publication de l'image sur GHCR (job `publish`).

Le CronJob (`--mode process`, toutes les 5 minutes) ne génère jamais de données : il traite
seulement les nouveaux fichiers du bucket.

## Infrastructure as code (OpenTofu)

Le dossier `infra/` décrit l'infrastructure de production dans le cloud (Scaleway, région de
Paris), au lieu de la créer à la main :

| Fichier | Ressources |
|---|---|
| `network.tf` | Réseau privé partagé entre le cluster et la base |
| `kubernetes.tf` | Cluster Kubernetes managé (Kapsule) et son pool de noeuds |
| `database.tf` | PostgreSQL 16 managé, base `pipeline` (accessible uniquement par le réseau privé) |
| `storage.tf` | Bucket S3, identité IAM dédiée à la pipeline et sa clé d'accès |
| `outputs.tf` | Valeurs à injecter : `DATABASE_URL`, `S3_ENDPOINT_URL`, `S3_BUCKET`, clés S3, kubeconfig |

**État d'avancement : la configuration est validée mais n'a jamais été appliquée** (pas de
compte cloud). `tofu fmt` et `tofu validate` passent avec le vrai schéma du provider, et la
CI (`infra.yml`) les rejoue à chaque modification, sans identifiants. Le comportement réel
(valeurs des types de machines, droits IAM, coûts) n'a donc pas été vérifié sur le cloud.

Utilisation prévue :

```bash
cd infra
export SCW_ACCESS_KEY=... SCW_SECRET_KEY=...   # identifiants Scaleway
export TF_VAR_db_password='un-mot-de-passe-long'
cp terraform.tfvars.example terraform.tfvars   # puis le compléter
tofu init && tofu plan
tofu apply
tofu destroy                                   # à ne pas oublier : ces services sont payants
```

Le fichier d'état (`terraform.tfstate`) contient des secrets : il ne doit jamais être commité.
Le code de la pipeline n'a pas à changer : en production, PostgreSQL et SeaweedFS du cluster
sont remplacés par la base et le S3 managés, et la pipeline les rejoint via ses variables
d'environnement. Le déploiement du CronJob sur ce cluster (Secret créé à partir des sorties
OpenTofu) reste à écrire.

## Limites et pistes d'amélioration

- Le cluster de la CD est éphémère : il prouve que le déploiement fonctionne, mais aucun
  environnement ne reste en place.
- L'image déployée est l'image locale `data-pipeline:deploy` ; en production, on déploierait
  l'image publiée, taguée par commit.
- `requirements.txt` mélange dépendances d'exécution et d'outillage (pytest, ruff) : à
  séparer pour alléger l'image. L'image devrait aussi tourner avec un utilisateur non-root.
- SeaweedFS et PostgreSQL tournent chacun en une seule instance, sans sauvegarde ni
  haute disponibilité.
- Gestion des secrets : adaptée à un TP (secrets générés au déploiement) ; en production, un
  gestionnaire de secrets dédié serait préférable.
