# Market Screener Documentation Index

Bienvenue dans la documentation du Market Screener. Utilisez ce guide pour naviguer dans les différents aspects du projet.

## 📋 Navigation

### Aperçu & Architecture
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Architecture globale, composants, flux de données
- **[ROADMAP.md](ROADMAP.md)** — Historique des changements, milestones complétés et futurs

### Fonctionnalités Clés
- **[FUNDAMENTALS_ENRICHMENT.md](FUNDAMENTALS_ENRICHMENT.md)** — Enrichissement des données fondamentales (PER, PBR, ROE, etc.) avec yfinance et fallback Finnhub
- **[SCHEDULED_REFRESH.md](SCHEDULED_REFRESH.md)** — Pipeline Airflow pour refreshs intraday (30 min) et nightly
- **[API_ENDPOINTS.md](API_ENDPOINTS.md)** — Endpoints REST disponibles et leur utilisation

### Déploiement & Opérations
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Guide de déploiement local, Docker Compose, OVH
- **[ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)** — Configuration via variables d'environnement
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — Diagnostics courants et solutions

## 🚀 Quick Start

### Démarrer le développement local
```bash
cd market_screener
docker-compose down -v  # Reset volumes si nécessaire
docker-compose up -d --build
```

### Accéder aux services
- **API Backend:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **Screener UI:** http://localhost:3000
- **Airflow Dashboard:** http://localhost:8080

### Déclencher l'enrichissement fondamentaux manuellement
```bash
curl -X POST 'http://localhost:8000/api/v1/admin/fundamentals/enrich?limit=85&aggressive=true'
```

## 📊 Statut Courant (11 avril 2026)

✅ **Opérationnel:**
- API Backend: Healthy
- PostgreSQL 16: Healthy
- Frontend Screener: Loaded
- Airflow Scheduler: Active
- Airflow Webserver: Active

✅ **Données:**
- 40 stocks chargés avec données de marché
- 40 stocks (100%) enrichis avec données fondamentales (PER, PBR, ROE, etc.)
- Rafraîchissement intraday: Toutes les 30 minutes via Airflow
- Rafraîchissement nightly: Une fois par jour pour consolidation

**Fallback Finnhub:** Activé automatiquement quand yfinance est rate-limité (gratuit, 60 req/min)

## 🔄 Flux de Données

```
┌─────────────────────────────────────────────────────────┐
│             Market Screener Data Flow                    │
└─────────────────────────────────────────────────────────┘

Startup:
  1. Multi-pass refresh (yfinance) → PostgreSQL
  2. Identity-only fallback si pas de données
  3. Background top-up passes (récupère plus de rows)
  4. Fundamentals daemon bootstrap (aggressive, 12 rounds)

Intraday (Airflow every 30 min):
  1. Fetch latest prices & technicals (light params)
  2. Update database
  3. Refresh screener UI

Nightly (Airflow once per day):
  1. Heavy refresh pass (min_valid=50, retries=4)
  2. Consolidate data quality
  3. Prepare for next day

Fundamentals Daemon (ongoing):
  1. Bootstrap: 5 min delay → 12 aggressive rounds (90s apart)
  2. Maintenance: Every 30 minutes with lighter concurrency
  3. Provider priority: yfinance (primary) → Finnhub (fallback on rate-limit)
```

## � Documentation complète

### Racine du projet

| Fichier | Description |
|---------|-------------|
| [../README.md](../README.md) | Guide d'introduction et quick start |
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | Vue d'ensemble architecture (racine) |
| [../PROJECT_DOCUMENTATION.md](../PROJECT_DOCUMENTATION.md) | Documentation technique complète |
| [../REFACTORING.md](../REFACTORING.md) | Historique des refactorisations et décisions |
| [../ROADMAP.md](../ROADMAP.md) | Roadmap générale du projet (racine) |
| [../DEPLOYMENT_OVH_AIRFLOW_PIPELINE.md](../DEPLOYMENT_OVH_AIRFLOW_PIPELINE.md) | Déploiement OVH pipeline Airflow |
| [../scripts/DEPLOYMENT_GUIDE.md](../scripts/DEPLOYMENT_GUIDE.md) | Guide d'automatisation du déploiement |

### Documentation (`docs/`)

| Fichier | Description |
|---------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture détaillée du système |
| [ROADMAP.md](ROADMAP.md) | Historique et milestones |
| [FUNDAMENTALS_ENRICHMENT.md](FUNDAMENTALS_ENRICHMENT.md) | Enrichissement fondamentaux (PER, PBR, ROE) avec yfinance/Finnhub |
| [SCHEDULED_REFRESH.md](SCHEDULED_REFRESH.md) | Pipelines Airflow intraday/nightly |
| [API_ENDPOINTS.md](API_ENDPOINTS.md) | Endpoints REST disponibles |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Déploiement local, Docker Compose, OVH |
| [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) | Variables d'environnement, configuration |
| [ENV_FILES.md](ENV_FILES.md) | Fichiers `.env`, secrets, templates |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Diagnostics courants et solutions |
| [INCIDENT_REPORT_2026-04-11_OVH_DEPLOYMENT.md](INCIDENT_REPORT_2026-04-11_OVH_DEPLOYMENT.md) | Post-mortem déploiement OVH 11 avril 2026 |
| [AGENT_DEPLOYMENT_GUARDRAILS.md](AGENT_DEPLOYMENT_GUARDRAILS.md) | Règles de sécurité pour agents IA |

---

## �📁 Structure des Fichiers

```
market_screener/
├── README.md                          # Guide d'introduction
├── ARCHITECTURE.md                   # Vue d'ensemble (racine)
├── docs/                             # ← Documentation détaillée
│   ├── INDEX.md                      # (vous êtes ici)
│   ├── ROADMAP.md                    # Historique et milestones
│   ├── ARCHITECTURE.md               # Architecture détaillée
│   ├── FUNDAMENTALS_ENRICHMENT.md    # Enrichissement fondamentaux
│   ├── SCHEDULED_REFRESH.md          # Pipelines Airflow
│   ├── API_ENDPOINTS.md              # Endpoints REST
│   ├── DEPLOYMENT.md                 # Guide déploiement
│   ├── ENVIRONMENT_VARIABLES.md      # Config env vars
│   └── TROUBLESHOOTING.md            # Diagnostics
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI app + lifespan
│   │   ├── fundamentals_refresh.py   # Enrichissement fondamentaux
│   │   ├── finnhub_fallback.py       # Fallback Finnhub (NEW)
│   │   ├── yahoo_finance.py          # Yahoo data fetcher
│   │   ├── pipeline_refresh.py       # Multi-pass refresh
│   │   ├── config.py                 # Settings (env-driven)
│   │   ├── routes.py                 # API endpoints
│   │   └── models.py                 # SQLAlchemy ORM
│   └── requirements.txt               # Python deps (+requests for Finnhub)
├── airflow/
│   └── dags/
│       ├── market_screener_intraday_pipeline.py   # 30 min refresh
│       └── market_screener_nightly_pipeline.py    # Nightly refresh
├── frontend/                         # React/Vite screener UI
├── deploy/                           # OVH/K8s deployment configs
└── docker-compose.yml                # Local dev stack
```

## 🔧 Configuration Clés

### Tous les paramètres de rafraîchissement sont configurable via `.env`

```env
# Airflow intraday (every 30 min)
AIRFLOW_INTRADAY_FETCH_MIN_VALID=24
AIRFLOW_INTRADAY_RETRIES=2

# Airflow nightly
AIRFLOW_NIGHTLY_FETCH_MIN_VALID=50
AIRFLOW_NIGHTLY_RETRIES=4

# Fundamentals enrichment daemon
FUNDAMENTALS_ENABLED=True
FUNDAMENTALS_BOOTSTRAP_ROUNDS=12         # local
FUNDAMENTALS_BOOTSTRAP_INITIAL_DELAY_SECONDS=300.0
FUNDAMENTALS_BOOTSTRAP_INTERVAL_SECONDS=90.0
FUNDAMENTALS_MAINTENANCE_INTERVAL_SECONDS=1800.0  # 30 min
FUNDAMENTALS_ROUND_LIMIT=120
FUNDAMENTALS_ONLY_MISSING=True
```

## 📞 Support & Ressources

- **Issues:** Consultez TROUBLESHOOTING.md pour diagnostics courants
- **API Documentation:** http://localhost:8000/docs (Swagger UI)
- **Airflow Dashboard:** http://localhost:8080 pour visualiser les DAGs
- **Logs:** `docker compose logs -f backend` pour logs en temps réel

---

**Document généré:** 11 avril 2026  
**Dernière mise à jour:** Implémentation du fallback Finnhub gratuit pour fundamentals enrichment
