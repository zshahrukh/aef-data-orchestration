project = "<PROJECT_ID>"
region  = "us-central1"

data_transformation_project = "<PROJECT_ID>"
environment                 = "dev"

deploy_cloud_workflows      = true
workflows_log_level         = "LOG_ERRORS_ONLY"

deploy_composer_dags        = true
create_composer_environment = true
composer_config             = {
  environment_size = "ENVIRONMENT_SIZE_SMALL"
  software_config  = {
    image_version = "composer-2-airflow-2"
    cloud_data_lineage_integration = true
  }
  workloads_config = {
    scheduler = {
      cpu        = 0.5
      memory_gb  = 1.875
      storage_gb = 1
      count      = 1
    }
    web_server = {
      cpu        = 0.5
      memory_gb  = 1.875
      storage_gb = 1
    }
    triggerer = {
      cpu        = 0.5
      memory_gb  = 1.875
      count      = 1
    }
    worker = {
      cpu        = 0.5
      memory_gb  = 1.875
      storage_gb = 1
      min_count  = 1
      max_count  = 3
    }
  }
}

# do not set in prod deployment, only needed for demo
enable_peering_to_sample_vpc = true
sample_vpc_self_link = "https://www.googleapis.com/compute/v1/projects/<PROJECT_ID>/global/networks/sample-vpc"