# Cloud Development Guide

This guide covers deployment and operations for Discount Tracker on Google Cloud Platform (GCP), using Terraform as the source of truth.

---

## 1. Prerequisites

Install and verify:

1. Google Cloud CLI
2. Terraform
3. A GCP project with billing enabled

Authenticate:

```bash
gcloud auth application-default login
gcloud config set project <PROJECT_ID>
```

---

## 2. Provision Infrastructure (Terraform)

From the project root:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit terraform.tfvars and set:

1. project_id
2. zone, machine_type (optional overrides)
3. github_repo_url
4. env_file_content (full .env content)

Important env vars for orchestrator/dbt:

1. DB_HOST
2. DB_NAME
3. DB_USER
4. DB_PASSWORD
5. POSTGRES_DB_PORT
6. DBT_PROFILES_DIR
7. DBT_PROJECT_DIR
8. UV_LINK_MODE

Apply infrastructure:

```bash
terraform init
terraform plan
terraform apply
```

Terraform provisions:

1. Compute Engine VM
2. Firewall rules (Streamlit, pgAdmin, Postgres, SSH)
3. Startup script bootstrap (swap, Docker, uv, make, repo clone, docker compose up)

---

## 3. Monitor Startup Script

From your local machine:

```bash
gcloud compute instances tail-serial-port-output discount-tracker-vm --zone=<ZONE> --port=1
```

From inside VM:

```bash
sudo journalctl -u google-startup-scripts.service -f
```

Exit log stream with Ctrl+C.

---

## 4. Access and Run Pipeline

SSH into VM:

```bash
gcloud compute ssh discount-tracker-vm --zone=<ZONE>
```

Switch to ubuntu user:

```bash
sudo -iu ubuntu
```

Run pipeline:

```bash
cd ~/discount-tracker
make run-orchestrator-test
```

Verify containers:

```bash
docker ps
```

---

## 5. Apply Config Changes Safely

When you edit any Terraform-managed setting (terraform.tfvars, startup script, firewall, VM config):

```bash
cd terraform
terraform apply
```

If startup behavior must rerun immediately:

```bash
gcloud compute instances reset discount-tracker-vm --zone=<ZONE>
```

---

## 6. Stop, Start, Destroy

Stop VM (keep disk/data):

```bash
gcloud compute instances stop discount-tracker-vm --zone=<ZONE>
```

Start VM again:

```bash
gcloud compute instances start discount-tracker-vm --zone=<ZONE>
```

Destroy all Terraform-managed resources:

```bash
cd terraform
terraform destroy
```

---

## 7. Optional Cron Schedule

On VM:

```bash
crontab -e
```

Add:

```cron
0 0 * * * /usr/bin/docker exec discount_orchestrator python /app/orchestrate.py --itemcount 10 >> /home/ubuntu/logs/cron/sync_$(date +\%Y-\%m-\%d).log 2>&1
```

Ensure logs path exists:

```bash
mkdir -p /home/ubuntu/logs/cron
```