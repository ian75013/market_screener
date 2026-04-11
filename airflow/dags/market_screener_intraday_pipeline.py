from __future__ import annotations

from datetime import datetime, timedelta
import os
import requests

from airflow import DAG
from airflow.operators.python import PythonOperator

BACKEND_URL = "http://backend:8000"
PIPELINE_ENDPOINT = f"{BACKEND_URL}/api/v1/admin/pipeline/run"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"

INTRADAY_CRON = os.getenv("AIRFLOW_INTRADAY_CRON", "*/30 6-22 * * 1-5")
INTRADAY_MIN_REQUIRED = int(os.getenv("AIRFLOW_INTRADAY_MIN_REQUIRED", "8"))
INTRADAY_FETCH_MIN_VALID = int(os.getenv("AIRFLOW_INTRADAY_FETCH_MIN_VALID", "24"))
INTRADAY_PROVIDER_RETRIES = int(os.getenv("AIRFLOW_INTRADAY_PROVIDER_RETRIES", "2"))
INTRADAY_PROVIDER_RETRY_DELAY_SECONDS = float(
    os.getenv("AIRFLOW_INTRADAY_PROVIDER_RETRY_DELAY_SECONDS", "2")
)


def _check_backend_health() -> None:
    response = requests.get(HEALTH_ENDPOINT, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "healthy":
        raise RuntimeError(f"Backend not healthy: {payload}")


def _run_intraday_pipeline() -> None:
    params = {
        "min_required": INTRADAY_MIN_REQUIRED,
        "fetch_min_valid": INTRADAY_FETCH_MIN_VALID,
        "region": "world",
        "include_alpaca_fallback": "true",
        "provider_retries": INTRADAY_PROVIDER_RETRIES,
        "provider_retry_delay_seconds": INTRADAY_PROVIDER_RETRY_DELAY_SECONDS,
        "enable_technical_fallback": "true",
    }
    response = requests.post(PIPELINE_ENDPOINT, params=params, timeout=300)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("updated"):
        raise RuntimeError(f"Intraday pipeline failed: {payload}")


def _verify_data_freshness() -> None:
    response = requests.get(f"{BACKEND_URL}/api/v1/stats", timeout=30)
    response.raise_for_status()
    payload = response.json()
    total = payload.get("total_stocks", 0)
    if total < INTRADAY_MIN_REQUIRED:
        raise RuntimeError(f"Unexpectedly low stock count after intraday pipeline: {total}")


default_args = {
    "owner": "market-screener",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="market_screener_intraday_pipeline",
    description="Regular gentle intraday refresh with local metric calculation",
    default_args=default_args,
    start_date=datetime(2026, 4, 1),
    schedule=INTRADAY_CRON,
    catchup=False,
    tags=["market-screener", "intraday", "multi-source"],
    max_active_runs=1,
) as dag:
    check_backend_health = PythonOperator(
        task_id="check_backend_health",
        python_callable=_check_backend_health,
    )

    run_intraday_pipeline = PythonOperator(
        task_id="run_intraday_pipeline",
        python_callable=_run_intraday_pipeline,
        execution_timeout=timedelta(minutes=8),
    )

    verify_data_freshness = PythonOperator(
        task_id="verify_data_freshness",
        python_callable=_verify_data_freshness,
    )

    check_backend_health >> run_intraday_pipeline >> verify_data_freshness
