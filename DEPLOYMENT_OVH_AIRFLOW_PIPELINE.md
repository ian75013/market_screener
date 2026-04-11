# Documentation Complete - Market Screener (Local + OVH VPS + Airflow + OpenVPN)

## 1. Objectif

Ce document résume l'ensemble des développements réalisés pour obtenir:

- une exécution locale simple pour tester
- un déploiement VPS OVH sécurisé et automatisé
- un Airflow privé sur VPN (OpenVPN)
- un pipeline de refresh multi-source robuste (retries + fallback calcul automatique)
- une configuration administrable par variables d'environnement
- un mécanisme de rollback minimal en cas d'échec

---

## 2. Ce qui a été ajouté/modifié

### 2.1 Pipeline de données multi-pass (backend)

Fichier: `backend/app/pipeline_refresh.py`

Ajouts principaux:

- orchestration multi-pass (universe, fetch provider, enrichissement local, quality gate, upsert)
- retries provider configurables
- fallback provider (Yahoo -> Alpaca si disponible)
- fallback automatique de calcul technique pour compléter des champs manquants

Paramètres clés du pipeline:

- `min_required`
- `region`
- `include_alpaca_fallback`
- `provider_retries`
- `provider_retry_delay_seconds`
- `enable_technical_fallback`

### 2.2 API admin pipeline enrichie

Fichier: `backend/app/routes.py`

Endpoint:

- `POST /api/v1/admin/pipeline/run`

Nouveaux query params:

- `provider_retries`
- `provider_retry_delay_seconds`
- `enable_technical_fallback`

Endpoint profil:

- `GET /api/v1/admin/pipeline/profiles`

### 2.3 DAG Airflow configurés pour la résilience

Fichiers:

- `airflow/dags/market_screener_intraday_pipeline.py`
- `airflow/dags/market_screener_nightly_pipeline.py`

Comportement:

- appel API pipeline avec retries provider
- fallback technique automatique activé
- validations post-refresh

---

## 3. Configuration Local (test)

### 3.1 Principe

En local, Airflow est volontairement exposé en localhost uniquement.

Fichier de référence: `.env.example`

Valeurs locales recommandées:

- `AIRFLOW_BIND_HOST=127.0.0.1`
- `AIRFLOW_PORT=8088`

### 3.2 Credentials admin Airflow paramétrés

Le compte admin Airflow n'est plus hardcodé.

Variables:

- `AIRFLOW_ADMIN_USERNAME`
- `AIRFLOW_ADMIN_PASSWORD`
- `AIRFLOW_ADMIN_FIRSTNAME`
- `AIRFLOW_ADMIN_LASTNAME`
- `AIRFLOW_ADMIN_EMAIL`

Le service `airflow-init` dans `docker-compose.yml` utilise ces variables pour créer l'utilisateur admin.

---

## 4. Configuration Production OVH VPS

### 4.1 Fichiers clés

- `deploy/docker-compose.ovh.yml`
- `deploy/scripts/env.ovh.example`
- `deploy/scripts/env.ovh`
- `scripts/deploy_market_screener_ovh.sh`
- `scripts/sync_to_vps.sh`
- `deploy/scripts/install_apache_site.sh`

### 4.2 Domaine et sous-domaines

Configuration retenue:

- app: `market.screener.doctumconsilium.com`
- api: `api.market.screener.doctumconsilium.com`

### 4.3 Répertoire cible VPS

- `APP_DIR=/opt/market_screener`

### 4.4 Airflow sur OpenVPN

Configuration attendue:

- `AIRFLOW_BIND_HOST=10.8.0.1`
- `AIRFLOW_REQUIRE_VPN=true`

Le script de déploiement vérifie que l'IP est dans une plage privée/VPN autorisée.

Plages acceptées:

- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`
- `100.64.0.0/10`

Si l'IP ne correspond pas, le déploiement échoue volontairement.

---

## 5. Sécurité et exposition réseau

### 5.1 En prod OVH (override)

Ports bindés en local/VPN selon variables:

- PostgreSQL: loopback par défaut
- Backend API: loopback par défaut
- Frontend: loopback par défaut
- Airflow: IP VPN requise

Le frontal public est assuré par Apache (ou autre reverse proxy host).

### 5.2 HTTPS automatique (Certbot)

Le script Apache peut provisionner automatiquement les certificats.

Variables:

- `APACHE_AUTOCONFIG=true`
- `CERTBOT_AUTOCONFIG=true`
- `CERTBOT_EMAIL=...`

Prérequis:

- DNS des domaines pointant vers le VPS
- ports 80/443 ouverts

---

## 6. Déploiement automatisé OVH

### 6.1 Sync

Script: `scripts/sync_to_vps.sh`

Fonction:

- synchronisation repository via SSH/rsync
- copie sécurisée du `.env`

### 6.2 Déploiement remote

Script: `scripts/deploy_market_screener_ovh.sh`

Fonction:

- installation Docker si absent
- `docker compose up -d --build --wait`
- checks de santé
- rollback minimal si échec (si activé)

Variables de robustesse:

- `DEPLOY_WAIT_TIMEOUT`
- `ROLLBACK_ON_FAILURE`

### 6.3 Rollback minimal

Avant rebuild:

- tag backup images backend/frontend

En cas d'échec santé:

- retag des images backup
- tentative de redémarrage de la dernière version stable

---

## 7. Résilience du pipeline marché

### 7.1 Retry provider

Le fetch marché est réessayé automatiquement avec:

- nombre de tentatives configurable
- délai entre tentatives configurable

### 7.2 Fallback provider

Stratégie:

- Yahoo en primaire
- Alpaca en fallback (si credentials présents)

### 7.3 Fallback calcul technique automatique

Si certaines métriques techniques sont absentes, calcul de substitution pour maintenir un dataset exploitable:

- `change_3m` / `change_6m` (proxy)
- `rsi` (proxy momentum)
- `dist_mm50` / `dist_mm200`
- `volatility`
- cohérence bornes 52w

Objectif:

- éviter qu'un run échoue uniquement pour données incomplètes
- conserver un niveau de qualité minimal pour le screener

---

## 8. Variables d'environnement importantes

### 8.1 Local

- `AIRFLOW_BIND_HOST=127.0.0.1`
- `AIRFLOW_PORT=8088`
- `AIRFLOW_ADMIN_*`

### 8.2 OVH

- `APP_DIR=/opt/market_screener`
- `APP_DOMAIN=market.screener.doctumconsilium.com`
- `API_DOMAIN=api.market.screener.doctumconsilium.com`
- `VITE_API_URL=https://api.market.screener.doctumconsilium.com/api/v1`
- `AIRFLOW_BIND_HOST=10.8.0.1`
- `AIRFLOW_REQUIRE_VPN=true`
- `APACHE_AUTOCONFIG=true`
- `CERTBOT_AUTOCONFIG=true`
- `CERTBOT_EMAIL=admin@doctumconsilium.com`
- `DEPLOY_WAIT_TIMEOUT=300`
- `ROLLBACK_ON_FAILURE=true`

---

## 9. Runbook d'exécution

### 9.1 Test local

1. Copier `.env.example` vers `.env`
2. Ajuster les variables locales
3. Lancer:

```bash
docker compose up --build
```

4. Vérifier:

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000/health`
- Airflow: `http://localhost:8088`

### 9.2 Déploiement OVH

1. Préparer `deploy/scripts/env.ovh`
2. Renseigner SSH et host
3. Lancer:

```bash
./scripts/deploy_market_screener_ovh.sh deploy/scripts/env.ovh
```

4. Vérifier:

- reverse proxy HTTP/HTTPS
- API domaine
- App domaine
- accès Airflow via VPN OpenVPN uniquement

---

## 10. Checklist validation finale

- [ ] Airflow local uniquement sur `127.0.0.1`
- [ ] Airflow prod sur `10.8.0.1`
- [ ] `AIRFLOW_REQUIRE_VPN=true`
- [ ] credentials admin Airflow personnalisés
- [ ] Certbot provisionné et certificats valides
- [ ] pipeline DAG intraday/nightly actifs
- [ ] fallback provider et fallback technique fonctionnels
- [ ] rollback minimal testé

---

## 11. Références dans le repo

- `docker-compose.yml`
- `.env.example`
- `backend/app/pipeline_refresh.py`
- `backend/app/routes.py`
- `airflow/dags/market_screener_intraday_pipeline.py`
- `airflow/dags/market_screener_nightly_pipeline.py`
- `deploy/docker-compose.ovh.yml`
- `deploy/scripts/env.ovh.example`
- `deploy/scripts/env.ovh`
- `deploy/scripts/install_apache_site.sh`
- `scripts/sync_to_vps.sh`
- `scripts/deploy_market_screener_ovh.sh`
- `scripts/DEPLOYMENT_GUIDE.md`
