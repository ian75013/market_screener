# Airflow Pipelines — Architecture k3s

## Fonctionnement

Les DAGs market_screener sont entièrement basés sur des appels HTTP vers le backend
(pas d'imports de code local). Ils sont compatibles k3s nativement.

## Problème résolu

Le ConfigMap `market-screener-airflow-dags` n'était pas défini dans le template k3s —
il était censé être généré par un script de déploiement inexistant.
Il est maintenant inline dans `k3s-fromOVHVps/deploy/platform/50-market-screener.template.yaml`.

## URL Backend

Les DAGs utilisent `http://market-screener-backend:8000` (nom court Kubernetes).
Dans le namespace `market-screener`, cette résolution DNS est valide.

## Pipelines

| DAG | Schedule | Description |
|---|---|---|
| `market_screener_intraday_pipeline` | `*/30 6-22 * * 1-5` | Refresh intraday toutes les 30 min (jours ouvrés) |
| `market_screener_nightly_pipeline` | `15 2 * * 1-5` | Refresh complet nocturne + quality gates |

## Providers de données (gratuits)

Les pipelines utilisent uniquement des providers configurés côté backend.
Pas de clé API requise pour le pipeline de base (yfinance en fallback).

## Accès Airflow UI

Disponible sur `https://products.doctumconsilium.com/tools/airflow/`
(protégé Keycloak via oauth2-proxy).
