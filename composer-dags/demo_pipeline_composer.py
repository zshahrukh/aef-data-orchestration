# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# --------------------------------------------------------------------------------
# Load The Dependencies
# --------------------------------------------------------------------------------

import json
import uuid
import re
from airflow import models
import google.auth
from airflow.models.variable import Variable
from airflow.providers.google.cloud.operators.dataflow import DataflowStartFlexTemplateOperator
from airflow.operators import empty
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.utils.task_group import TaskGroup
from airflow.providers.google.cloud.operators.bigquery import  BigQueryInsertJobOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.sensors.dataform import DataformWorkflowInvocationStateSensor
from airflow.providers.google.cloud.operators.dataform import (
    DataformCreateCompilationResultOperator,
    DataformCreateWorkflowInvocationOperator,
)
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocCreateBatchOperator,
    DataprocGetBatchOperator
)
from airflow.providers.google.cloud.sensors.dataproc import DataprocBatchSensor
from google.cloud.dataform_v1beta1 import WorkflowInvocation
from google.cloud import storage
from datetime import datetime, timedelta

# --------------------------------------------------------------------------------
# Read variables from GCS parameters file for the job
# --------------------------------------------------------------------------------
storage_client = storage.Client()
jobs_bucket = Variable.get("DATA_TRANSFORMATION_GCS_BUCKET")

batch_id = f"aef-{str(uuid.uuid4())}"

def extract_job_params(job_name, function_name, encoding='utf-8'):
    """Extracts parameters from a JSON job file.

    Args:
        bucket_name: Bucket containing the JSON parameters file .

    Returns:
        A dictionary containing the extracted parameters.
    """

    json_file_path = f'gs://{jobs_bucket}/{function_name}/{job_name}.json'

    parts = json_file_path.replace("gs://", "").split("/")
    bucket_name = parts[0]
    object_name = "/".join(parts[1:])
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    json_data = blob.download_as_bytes()
    params = json.loads(json_data.decode(encoding))
    return params


# --------------------------------------------------------------------------------
# Set default arguments
# --------------------------------------------------------------------------------

# If you are running Airflow in more than one time zone
# see https://airflow.apache.org/docs/apache-airflow/stable/timezone.html
# for best practices
yesterday = datetime.now() - timedelta(days=1)

default_args = {
    'owner': 'airflow',
    'start_date': yesterday,
    'depends_on_past': False,
    'email': [''],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5)
}

sample_serverless_spark_mainframe_ingestion = extract_job_params('sample_serverless_spark_mainframe_ingestion','dataproc-serverless-job-executor')
for key, value in sample_serverless_spark_mainframe_ingestion.items():
	default_args['sample_serverless_spark_mainframe_ingestion'+key] = value

sample_jdbc_dataflow_ingestion = extract_job_params('sample_jdbc_dataflow_ingestion','dataflow-flextemplate-job-executor')
for key, value in sample_jdbc_dataflow_ingestion.items():
	default_args['sample_jdbc_dataflow_ingestion'+key] = value

run_dataform_tag = extract_job_params('run_dataform_tag','dataform-tag-executor')
for key, value in run_dataform_tag.items():
	default_args['run_dataform_tag'+key] = value


start_date_str = yesterday.strftime('%Y-%m-%d')
end_date_str = datetime.today().strftime('%Y-%m-%d')
# --------------------------------------------------------------------------------
# Main DAG
# --------------------------------------------------------------------------------

with models.DAG(
        'demo_pipeline_composer',
        default_args=default_args,
        params={
            "start_date_str": start_date_str,
            "end_date_str": end_date_str
        },
        catchup=False,
        schedule_interval=None) as dag:

    start = empty.EmptyOperator(
        task_id='start',
        trigger_rule='all_success'
    )

        # Start level group definition
    with TaskGroup(group_id="Level_1") as tg_Level_1:
                   # Start thread group definition
           with TaskGroup(group_id="Level_1_Thread_1") as tg_level_1_Thread_1:
                    with TaskGroup(group_id="sample_serverless_spark_mainframe_ingestion") as sample_serverless_spark_mainframe_ingestion:

                           def push_batch_id_to_xcom(**context):
                               context['task_instance'].xcom_push(key='batch-id', value=batch_id)

                           push_batch_id_to_xcom_sample_serverless_spark_mainframe_ingestion = PythonOperator(
                               task_id='batch_id',
                               python_callable=push_batch_id_to_xcom,
                               provide_context=True
                           )

                           # create batch
                           create_batch_for_sample_serverless_spark_mainframe_ingestion = DataprocCreateBatchOperator(
                               task_id="create_batch_for_sample_serverless_spark_mainframe_ingestion",
                               batch={
                                   "spark_batch": {
                                       "jar_file_uris": [default_args['sample_serverless_spark_mainframe_ingestion' + 'jar_file_location']],
                                       "main_class": default_args['sample_serverless_spark_mainframe_ingestion' + 'spark_app_main_class'],
                                       "args": default_args['sample_serverless_spark_mainframe_ingestion' + 'spark_args'],
                                   },
                                   "runtime_config": {
                                       "version": default_args['sample_serverless_spark_mainframe_ingestion' + 'dataproc_serverless_runtime_version'],
                                       "properties": default_args['sample_serverless_spark_mainframe_ingestion' + 'spark_app_properties'],
                                   },
                                   "environment_config": {
                                       "execution_config": {
                                           "service_account": default_args['sample_serverless_spark_mainframe_ingestion' + 'dataproc_service_account'],
                                           "subnetwork_uri": f"projects/{default_args['sample_serverless_spark_mainframe_ingestion' + 'dataproc_serverless_project_id']}/{default_args['sample_serverless_spark_mainframe_ingestion' + 'subnetwork']}"
                                       }
                                   }
                               },
                               batch_id="{{ task_instance.xcom_pull(task_ids='Level_1.Level_1_Thread_1.sample_serverless_spark_mainframe_ingestion.batch_id', key='batch-id') }}",
                               project_id=default_args['sample_serverless_spark_mainframe_ingestion' + 'dataproc_serverless_project_id'],
                               region=default_args['sample_serverless_spark_mainframe_ingestion' + 'dataproc_serverless_region'],
                               deferrable=True
                           )

                           wait_for_batch_completion_for_sample_serverless_spark_mainframe_ingestion = DataprocBatchSensor(
                               task_id='wait_for_batch_completion_for_sample_serverless_spark_mainframe_ingestion',
                               batch_id="{{ task_instance.xcom_pull(task_ids='Level_1.Level_1_Thread_1.sample_serverless_spark_mainframe_ingestion.batch_id', key='batch-id') }}",
                               region=default_args['sample_serverless_spark_mainframe_ingestion' + 'dataproc_serverless_region'],
                               poke_interval=400,
                               timeout=3600,
                               soft_fail=True
                           )

                           get_batch_for_sample_serverless_spark_mainframe_ingestion = DataprocGetBatchOperator(
                               task_id="get_batch_for_sample_serverless_spark_mainframe_ingestion",
                               batch_id="{{ task_instance.xcom_pull(task_ids='Level_1.Level_1_Thread_1.sample_serverless_spark_mainframe_ingestion.batch_id', key='batch-id') }}",
                               region=default_args['sample_serverless_spark_mainframe_ingestion' + 'dataproc_serverless_region']
                           )

                           push_batch_id_to_xcom_sample_serverless_spark_mainframe_ingestion >> create_batch_for_sample_serverless_spark_mainframe_ingestion >> wait_for_batch_completion_for_sample_serverless_spark_mainframe_ingestion >> get_batch_for_sample_serverless_spark_mainframe_ingestion


                    sample_serverless_spark_mainframe_ingestion
           # End thread group definition           # Start thread group definition
           with TaskGroup(group_id="Level_1_Thread_2") as tg_level_1_Thread_2:
                    with TaskGroup(group_id="sample_jdbc_dataflow_ingestion") as sample_jdbc_dataflow_ingestion:
                        dataflow_job_name = re.sub(r"^\d+", "",re.sub(r"[^a-z0-9+]", "", "sample_jdbc_dataflow_ingestion"))
                        dataflow_job_name = re.sub(r"^\d+", "", dataflow_job_name)
                        gcs_path = "gs://dataflow-templates-{region}/{version}/flex/{template}".format(region=default_args['sample_jdbc_dataflow_ingestion'+'dataflow_location'],
                                                                                                       version=default_args['sample_jdbc_dataflow_ingestion'+'dataflow_template_version'],
                                                                                                       template=default_args['sample_jdbc_dataflow_ingestion'+'dataflow_template_name'])
                        body = {
                            "launchParameter": {
                                "jobName": dataflow_job_name,
                                "parameters": default_args['sample_jdbc_dataflow_ingestion'+'dataflow_job_params'],
                                "containerSpecGcsPath": gcs_path,
                                "environment": {
                                    "tempLocation": "gs://{bucket}/dataflow/temp".format(bucket=default_args['sample_jdbc_dataflow_ingestion' + 'dataflow_temp_bucket']),
                                    "maxWorkers": str(default_args['sample_jdbc_dataflow_ingestion' + 'dataflow_max_workers']),
                                    "network": str(default_args['sample_jdbc_dataflow_ingestion' + 'network']),
                                    "subnetwork": str(default_args['sample_jdbc_dataflow_ingestion' + 'subnetwork'])}
                            }
                        }
                        dataflow_job_sample_jdbc_dataflow_ingestion = DataflowStartFlexTemplateOperator(
                            task_id="dataflow_flex_template_sample_jdbc_dataflow_ingestion",
                            location=default_args['sample_jdbc_dataflow_ingestion'+'dataflow_location'],
                            body=body
                        )

                        dataflow_job_sample_jdbc_dataflow_ingestion


                    sample_jdbc_dataflow_ingestion
           # End thread group definition

           tg_level_1_Thread_1
           tg_level_1_Thread_2
    # End level group definition
    # Start level group definition
    with TaskGroup(group_id="Level_2") as tg_Level_2:
                   # Start thread group definition
           with TaskGroup(group_id="Level_2_Thread_3") as tg_level_2_Thread_3:
                    with TaskGroup(group_id="run_dataform_tag") as run_dataform_tag:
                           # compilation
                           create_compilation_result_for_run_dataform_tag = DataformCreateCompilationResultOperator(
                               project_id=default_args['run_dataform_tag'+'dataform_project_id'],
                               region=default_args['run_dataform_tag'+'dataform_location'],
                               repository_id=default_args['run_dataform_tag'+'repository_name'],
                               task_id="compilation_task_run_dataform_tag",
                               compilation_result={
                                   "git_commitish": default_args['run_dataform_tag'+'branch'],
                                   "code_compilation_config": {
                                       "vars": {
                                            "start_date": "{{ params.start_date_str }}",
                                            "end_date": "{{ params.end_date_str }}"
                                       }
                                   }
                               }
                           )

                           # workflow invocation in dataform
                           create_workflow_run_dataform_tag_invocation = DataformCreateWorkflowInvocationOperator(
                               project_id=default_args['run_dataform_tag' + 'dataform_project_id'],
                               region=default_args['run_dataform_tag' + 'dataform_location'],
                               repository_id=default_args['run_dataform_tag' + 'repository_name'],
                               task_id='workflow_inv_run_dataform_tag',
                               asynchronous=True,
                               workflow_invocation={
                                   "compilation_result": "{{ task_instance.xcom_pull('Level_2.Level_2_Thread_3.run_dataform_tag.compilation_task_run_dataform_tag')['name'] }}",
                                   "invocation_config": { "included_tags": default_args['run_dataform_tag'+'tags'],
                                                          "transitive_dependencies_included": True
                                                        }
                               },
                               trigger_rule='all_success'
                           )

                           is_workflow_run_dataform_tag_invocation_done = DataformWorkflowInvocationStateSensor(
                               project_id=default_args['run_dataform_tag' + 'dataform_project_id'],
                               region=default_args['run_dataform_tag' + 'dataform_location'],
                               repository_id=default_args['run_dataform_tag' + 'repository_name'],
                               task_id="is_workflow_run_dataform_tag_invocation_done",
                               workflow_invocation_id=("{{ task_instance.xcom_pull('Level_2.Level_2_Thread_3.run_dataform_tag.workflow_inv_run_dataform_tag')['name'].split('/')[-1] }}"),
                               expected_statuses={WorkflowInvocation.State.SUCCEEDED},
                               failure_statuses={WorkflowInvocation.State.FAILED, WorkflowInvocation.State.CANCELLED},
                           )

                           create_compilation_result_for_run_dataform_tag >> create_workflow_run_dataform_tag_invocation >> is_workflow_run_dataform_tag_invocation_done


                    run_dataform_tag
           # End thread group definition

           tg_level_2_Thread_3
    # End level group definition


    end = empty.EmptyOperator(
        task_id='end',
        trigger_rule='all_success'
    )

    start >> tg_Level_1 >> tg_Level_2 >> end