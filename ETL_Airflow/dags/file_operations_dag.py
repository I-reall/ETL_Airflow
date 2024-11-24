# file_operations_dag.py

from datetime import datetime, timedelta
import os
import shutil
from airflow import DAG
from airflow.operators.python import PythonOperator

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
with DAG(
    'file_operations_dag',
    default_args=default_args,
    description='A simple DAG to create and move files',
    schedule_interval=None,  # Set to None for manual triggering
    start_date=datetime(2023, 10, 1),
    catchup=False,
) as dag:

    def create_file(**kwargs):
        """Creates a file in the DAGs folder."""
        file_path = os.path.join(os.environ['AIRFLOW_HOME'], 'dags', 'test_file.txt')
        with open(file_path, 'w') as f:
            f.write('This is a test file created by Airflow.')
        print(f'File created at {file_path}')

    def move_files(**kwargs):
        """Moves files from source directory to the plugins folder."""
        source_dir = os.path.join(os.environ['AIRFLOW_HOME'], 'dags')
        destination_dir = os.path.join(os.environ['AIRFLOW_HOME'], 'plugins')

        # Ensure the destination directory exists
        os.makedirs(destination_dir, exist_ok=True)

        for filename in os.listdir(source_dir):
            if filename.endswith('.txt'):
                src_file = os.path.join(source_dir, filename)
                dst_file = os.path.join(destination_dir, filename)
                shutil.move(src_file, dst_file)
                print(f'Moved {src_file} to {dst_file}')

    create_file_task = PythonOperator(
        task_id='create_file',
        python_callable=create_file,
        provide_context=True,
    )

    move_files_task = PythonOperator(
        task_id='move_files',
        python_callable=move_files,
        provide_context=True,
    )

    # Define task dependencies
    create_file_task >> move_files_task

    
