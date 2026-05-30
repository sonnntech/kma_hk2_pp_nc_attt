from __future__ import annotations

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except Exception:  # pragma: no cover
    DAG = None
    PythonOperator = None

from datetime import datetime

from pipeline.etl_pipeline import run_pipeline


if DAG is not None:
    with DAG(
        dag_id="blockchain_data_pipeline",
        start_date=datetime(2026, 1, 1),
        schedule="@daily",
        catchup=False,
    ) as dag:
        PythonOperator(task_id="run_pipeline", python_callable=run_pipeline)
