# Terraform Infrastructure Setup

This directory contains Terraform configurations to automate the provisioning of your Discount Tracker infrastructure on Google Cloud Platform (GCP).

## Quick Start

### Prerequisites

1. **Terraform installed** - Verify with `terraform version`
2. **GCP account and project** - [Create one here](https://console.cloud.google.com)
3. **GCP CLI installed** - [Installation guide](https://cloud.google.com/sdk/docs/install)
4. **Authenticated with GCP**:
   ```bash
   gcloud auth application-default login
   ```

### Setup Steps

1. **Copy the example configuration**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit `terraform.tfvars`** with your values:
   - `project_id`: Your GCP project ID
   - `github_repo_url`: Your GitHub repo URL (with authentication token if private)
   - `env_file_content`: Your `.env` file variables
   - `machine_type`: set up your machine size

3. **Initialize Terraform**:
   ```bash
   terraform init
   ```

4. **Review the plan**:
   ```bash
   terraform plan
   ```

5. **Apply the configuration**:
   ```bash
   terraform apply
   ```
   - Type `yes` when prompted
   - Wait for provisioning to complete (5-10 minutes)

6. **Get your VM details**:
   ```bash
   terraform output
   ```

## File Structure

- **`main.tf`** - Provider configuration and VM instance
- **`variables.tf`** - Input variable definitions
- **`firewall.tf`** - Firewall rules for Streamlit, PGAdmin, and Postgres
- **`outputs.tf`** - Output values (IP addresses, URLs, SSH commands)
- **`cloud-init.sh`** - Auto-provisioning script that runs on VM startup
- **`terraform.tfvars`** - Your configuration (DO NOT commit to Git)
- **`.gitignore`** - Protects sensitive Terraform files

## Common Commands

```bash
# Show current infrastructure state
terraform show

# Get output values
terraform output vm_external_ip
terraform output streamlit_url

# Destroy all resources (clean up when done)
terraform destroy

# Get SSH command for your VM
terraform output ssh_command

# See VM serial console stream for debugging
gcloud compute instances tail-serial-port-output [VM_NAME] --zone=[ZONE] --port=1

# Change into ubuntu user to run make commands inside VM
sudo -iu ubuntu
```

## What Gets Created

✅ **VM Instance** - Ubuntu 22.04 LTS (configurable machine type)  
✅ **Boot Disk** - 30GB persistent storage  
✅ **Firewall Rules** - Streamlit (8501), PGAdmin (8080), Postgres (5432), SSH (22)  
✅ **Public IP** - Ephemeral external IP address  
✅ **Auto-provisioning** - Docker, uv, make, swap, and Docker Compose startup via cloud-init

## Security Notes

🔒 **`terraform.tfvars` contains secrets** - Added to `.gitignore` automatically  
🔒 **Never commit `.tfvars` files to Git**  
🔒 **Rotate credentials regularly**  
🔒 For production, use [Terraform Cloud](https://www.terraform.io/cloud) or [GCS backend](https://www.terraform.io/language/settings/backends/gcs) for state management

## Troubleshooting

### VM not starting applications
Check the startup script logs:
```bash
gcloud compute instances get-serial-port-output discount-tracker-vm --zone=<ZONE>
```

### Docker Compose not running
SSH into the VM and check status:
```bash
docker ps
docker logs discount_orchestrator
```

### Firewall rules not working
Verify rules are created:
```bash
gcloud compute firewall-rules list --filter="name~'allow-'"
```
