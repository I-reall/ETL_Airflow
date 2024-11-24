from datetime import datetime, timedelta
import os
import pandas as pd
import pyreadstat
from sqlalchemy import create_engine
from airflow import DAG
from airflow.operators.python import PythonOperator

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
with DAG(
    'labour_force_survey_etl',
    default_args=default_args,
    description='ETL pipeline for Labour Force Survey',
    schedule_interval=None,  # Manual triggering
    start_date=datetime(2023, 11, 1),
    catchup=False,
) as dag:

    # Task 1: Read the .sav file and create trans_df
    def extract(**kwargs):
        # Define file path
        sav_file_path = os.path.join(os.environ['AIRFLOW_HOME'], 'dags', 'LabourForceSurvey_dummy.sav')
        
        # Read data and metadata
        df, meta = pyreadstat.read_sav(sav_file_path)

        # Create trans_df (translation DataFrame)
        column_labels = meta.column_labels  # Field descriptions
        value_labels = meta.variable_value_labels  # Value labels
        
        data = []
        for field, field_desc in zip(df.columns, column_labels):
            levels = "||".join(map(str, map(int, value_labels[field].keys()))) if field in value_labels else ""
            level_labels = "||".join(value_labels[field].values()) if field in value_labels else ""
            data.append({
                "field": field.lower(),
                "field_desc": field_desc,
                "levels": levels,
                "level_labels": level_labels,
                "branches": "Root~Demographics"
            })
        trans_df = pd.DataFrame(data)

        # Save to XCom for other tasks
        kwargs['ti'].xcom_push(key='trans_df', value=trans_df.to_dict())
        kwargs['ti'].xcom_push(key='data_df', value=df.to_dict())

    # Task 2: Validate the data
    def validate(**kwargs):
        # Retrieve DataFrames from XCom
        trans_df = pd.DataFrame(kwargs['ti'].xcom_pull(key='trans_df', task_ids='extract'))
        
        # Perform validation checks
        def has_duplicates(value_str):
            items = value_str.split("||")
            return len(items) != len(set(items))
        
        # Validation Results
        validation_results = []
        
        # Check for duplicate levels
        duplicated_levels = trans_df[trans_df['levels'].apply(has_duplicates)]
        if not duplicated_levels.empty:
            validation_results.append(f"Duplicated levels found: {len(duplicated_levels)} rows.")
        
        # Check for duplicate level labels
        duplicated_labels = trans_df[trans_df['level_labels'].apply(has_duplicates)]
        if not duplicated_labels.empty:
            validation_results.append(f"Duplicated level labels found: {len(duplicated_labels)} rows.")
        
        # Push validation results to XCom
        kwargs['ti'].xcom_push(key='validation_results', value="\n".join(validation_results))

    # Task 3: Load data into MySQL
    def load(**kwargs):
        from sqlalchemy import create_engine

        # Retrieve DataFrames from XCom
        trans_df = pd.DataFrame(kwargs['ti'].xcom_pull(key='trans_df', task_ids='extract'))
        data_df = pd.DataFrame(kwargs['ti'].xcom_pull(key='data_df', task_ids='extract'))

        # Database credentials
        mysql_host = 'mysql'  # Service name from docker-compose
        mysql_user = 'airflow'
        mysql_password = 'airflow'
        translation_db = 'translation_db'
        labour_fs_db = 'labour_fs_db'

        # Connect to MySQL using SQLAlchemy
        translation_engine = create_engine(
            f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{translation_db}"
        )
        labour_fs_engine = create_engine(
            f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{labour_fs_db}"
        )

        # Save trans_df to translation_db
        trans_df.to_sql(name='translation', con=translation_engine, if_exists='replace', index=False)

        # Save data_df to labour_fs_db
        data_df.to_sql(name='labour_force_survey', con=labour_fs_engine, if_exists='replace', index=False)

        print("Data loaded successfully into MySQL databases.")

    # Define Airflow tasks
    extract_task = PythonOperator(
        task_id='extract',
        python_callable=extract,
        provide_context=True,
    )

    validate_task = PythonOperator(
        task_id='validate',
        python_callable=validate,
        provide_context=True,
    )

    load_task = PythonOperator(
        task_id='load',
        python_callable=load,
        provide_context=True,
    )

    # Set task dependencies
    extract_task >> validate_task >> load_task
