from __future__ import annotations

from datetime import datetime, timedelta
import os
import requests

from airflow import DAG
from airflow.operators.python import PythonOperator

BACKEND_URL = "http://backend:8000"
PIPELINE_ENDPOINT = f"{BACKEND_URL}/api/v1/admin/pipeline/run"
FILTERS_ENDPOINT = f"{BACKEND_URL}/api/v1/filters"
STATS_ENDPOINT = f"{BACKEND_URL}/api/v1/stats"

NIGHTLY_CRON = os.getenv("AIRFLOW_NIGHTLY_CRON", "15 2 * * 1-5")
NIGHTLY_MIN_REQUIRED = int(os.getenv("AIRFLOW_NIGHTLY_MIN_REQUIRED", "20"))
NIGHTLY_FETCH_MIN_VALID = int(os.getenv("AIRFLOW_NIGHTLY_FETCH_MIN_VALID", "50"))
NIGHTLY_PROVIDER_RETRIES = int(os.getenv("AIRFLOW_NIGHTLY_PROVIDER_RETRIES", "4"))
NIGHTLY_PROVIDER_RETRY_DELAY_SECONDS = float(
    os.getenv("AIRFLOW_NIGHTLY_PROVIDER_RETRY_DELAY_SECONDS", "3")
)


def _run_nightly_pipeline() -> None:
    params = {
        "min_required": NIGHTLY_MIN_REQUIRED,
        "fetch_min_valid": NIGHTLY_FETCH_MIN_VALID,
        "region": "world",
        "include_alpaca_fallback": "true",
        "provider_retries": NIGHTLY_PROVIDER_RETRIES,
        "provider_retry_delay_seconds": NIGHTLY_PROVIDER_RETRY_DELAY_SECONDS,
        "enable_technical_fallback": "true",
    }
    response = requests.post(PIPELINE_ENDPOINT, params=params, timeout=600)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("updated"):
        raise RuntimeError(f"Nightly pipeline failed: {payload}")


def _validate_filter_options() -> None:
    response = requests.get(FILTERS_ENDPOINT, timeout=45)
    response.raise_for_status()
    payload = response.json()
    if payload.get("total_stocks", 0) < NIGHTLY_MIN_REQUIRED:
        raise RuntimeError("Filter options report insufficient stocks after nightly pipeline")

    required_ranges = ["market_cap", "change_3m", "change_6m", "dist_52w_high", "dist_52w_low"]
    ranges = payload.get("ranges", {})
    missing = [key for key in required_ranges if key not in ranges]
    if missing:
        raise RuntimeError(f"Missing required ranges: {missing}")


def _assert_distribution() -> None:
    response = requests.get(STATS_ENDPOINT, timeout=45)
    response.raise_for_status()
    payload = response.json()
    if payload.get("countries", 0) < 5:
        raise RuntimeError("Country diversity too low after nightly refresh")


default_args = {
    "owner": "market-screener",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="market_screener_nightly_pipeline",
    description="Nightly full refresh with quality checks for screener filters",
    default_args=default_args,
    start_date=datetime(2026, 4, 1),
    schedule=NIGHTLY_CRON,
    catchup=False,
    tags=["market-screener", "nightly", "quality-gate"],
    max_active_runs=1,
) as dag:
    run_nightly_pipeline = PythonOperator(
        task_id="run_nightly_pipeline",
        python_callable=_run_nightly_pipeline,
        execution_timeout=timedelta(minutes=12),
    )

    validate_filter_options = PythonOperator(
        task_id="validate_filter_options",
        python_callable=_validate_filter_options,
    )

    assert_distribution = PythonOperator(
        task_id="assert_distribution",
        python_callable=_assert_distribution,
    )

    run_nightly_pipeline >> validate_filter_options >> assert_distribution
