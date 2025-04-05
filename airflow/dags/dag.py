from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.dates import days_ago
import os

# Define DAG
default_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
    'retries': 1
}

with DAG(
    dag_id='gcs_to_k8s_pod_example_with_temp_gcs',
    default_args=default_args,
    schedule_interval='@weekly',
    schedule_interval=None,
    catchup=False
) as dag:

    # Task 2: Use KubernetesPodOperator to process the file from GCS
    fetch_products = KubernetesPodOperator(
        task_id='fetch-products-csv-file',
        name='fetch-products',
        namespace='default',
        image='...',
        cmds=["python", "fetch_products.py",
              "--search_period_start", None,
              "--search_period_end", None
              ],
        service_account_name='my-k8s-service-account',  # Use the KSA bound to the GSA
        is_delete_operator_pod=True,
    )

    fetch_products