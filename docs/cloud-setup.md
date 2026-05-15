# Cloud Setup Guide

This guide explains how to set up the current Discount Tracker architecture in Google Cloud. It is focused on the cloud deployment path only: Terraform provisions the infrastructure, Cloud Workflows orchestrates the pipeline, and Cloud Scheduler triggers the workflow on a schedule.

## Prerequisites

Before you start, make sure you have:

- A Google Cloud project with billing enabled
- Permission to create and manage Terraform resources in that project
- The following Google Cloud APIs enabled:
  - Cloud Run
  - Cloud Workflows
  - Cloud Scheduler
  - BigQuery
  - Cloud Storage
  - Logging
- Terraform installed locally
- Access to the repository and the ability to run `terraform` from the `terraform/` directory
- Docker images already published for the Cloud Run jobs referenced by Terraform:
  - `docker.io/vsantos77/discount-tracker-scrapy:v1.2`
  - `docker.io/vsantos77/discount-tracker-dbt:v1.2`
- A Google Cloud authentication method for Terraform, such as Application Default Credentials or a service account with sufficient permissions
- A BigQuery service account payload for the Streamlit app if you intend to run the dashboard against the deployed warehouse

Required runtime inputs:

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `TF_VAR_gcp_project_id`
- `TF_VAR_gcp_region`

## Guided Steps

### 1. Configure your Google Cloud project

Set up the target project, choose the deployment region, and make sure the APIs listed above are enabled. The Terraform configuration uses the project and region values consistently across GCS, BigQuery, Cloud Run, Workflows, and Scheduler.

### 2. Review the infrastructure layout

The cloud stack creates:

- a GCS bucket for raw landing files
- a BigQuery external table over the landing zone
- BigQuery datasets for bronze, silver, and gold layers
- Cloud Run jobs for scraping and dbt
- a Cloud Workflows workflow to orchestrate the jobs
- a Cloud Scheduler job that triggers the workflow weekly

This layout is important because the raw data, transformation layer, and dashboard are separated by design.

### 3. Export the Terraform variables

Set the project and region values expected by Terraform and the downstream jobs.

```bash
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-east1
export TF_VAR_gcp_project_id="$GCP_PROJECT_ID"
export TF_VAR_gcp_region="$GCP_REGION"
```

If you use a different shell or environment manager, set the same values there before applying Terraform.

### 4. Initialize Terraform

From the `terraform/` directory, initialize the providers and modules used by the stack.

```bash
cd terraform
terraform init
```

### 5. Review the plan

Inspect the proposed resources before applying them.

```bash
terraform plan
```

Confirm that the plan includes the GCS bucket, BigQuery datasets, Cloud Run jobs, Workflows resources, and Cloud Scheduler job.

### 6. Apply the infrastructure

Create the cloud resources.

```bash
terraform apply
```

After the apply completes, Terraform should have created the raw landing bucket, the BigQuery datasets, the service accounts, the Cloud Run jobs, the workflow, and the scheduled trigger.

### 7. Verify the orchestration path

The runtime control flow is:

- Cloud Scheduler triggers the Cloud Workflows execution
- Cloud Workflows launches the scraper Cloud Run job
- Cloud Workflows checks for newly created landing files
- Cloud Workflows launches the dbt Cloud Run job
- dbt materializes the bronze/silver/gold models in BigQuery

This means the workflow is not just a task runner; it is the orchestration layer that coordinates the pipeline end to end.

### 8. Validate the warehouse outputs

After the workflow runs successfully, confirm that:

- new objects exist in the GCS landing zone
- the BigQuery raw external table can read the landing files
- the dbt models are populated in the target datasets
- the dashboard-facing model is available for Streamlit queries

### 9. Connect the dashboard if needed

The Streamlit app reads credentials from `st.secrets`, not from Terraform-managed environment variables. If you are hosting the dashboard separately, provide the expected BigQuery service account information in the Streamlit secrets file before starting the app.

## Caveats

- This guide covers cloud deployment for the data platform, not local development setup.
- The Cloud Run job images referenced in Terraform must already exist in Docker Hub or whichever registry you choose to use. You can also build the images using the provided Dockerfile and point the terraform declarations to the images hosted on any image repository.
- The raw landing table uses hive partitioning with a partition filter, so queries should target the intended scraped-date partitions instead of scanning the whole bucket.
- dbt uses incremental models for faster repeated builds, so rerunning the workflow should update only the changed slices of the warehouse when possible.
- dbt tests and dbt-expectations rules are part of the deployment contract. If a model fails its checks, the pipeline should be treated as unhealthy until the data issue is resolved.
- The Streamlit app is a separate presentation layer and is not provisioned by the Terraform stack in this repository.
- Terraform resources assume the project IDs and region values in the configuration are correct; update them before applying if you are deploying to a different environment.
