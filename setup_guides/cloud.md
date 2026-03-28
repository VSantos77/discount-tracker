# Cloud Development Guide

This guide covers the deployment and management of the Discount Tracker on Google Cloud Platform (GCP). GCP is chosen for its reliable free tier for small VMs.

---

## 1. Initial Setup

1. **Install Google Cloud CLI**: Run the official installer.
2. **Authenticate**:

```bash
gcloud init
```

3. **Create Project**:

```bash
gcloud projects create [PROJECT_NAME]
```

4. **Set Active Project**:

```bash
gcloud config set project [PROJECT_NAME]
```

> Note: Keep project and account context updated before running infra commands.

## 2. Infrastructure Provisioning

### Create VM Instance

We use an `e2-micro` instance in `us-east1-c` to stay within the free tier.

```bash
gcloud compute instances create discount-tracker-vm \
    --zone=us-east1-c \
    --machine-type=e2-micro \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=30GB \
    --tags=http-server,streamlit-port
```

6. Allow firewall access to Streamlit app (and postgres, optionally)

```bash
# Allow Streamlit traffic
gcloud compute firewall-rules create allow-streamlit-8501 \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:8501 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=streamlit-port

# Allow PG Admin traffic

cloud compute firewall-rules create allow-pgadmin --allow tcp:8080 --target-tags=streamlit-port

# Allow Postgres traffic (Optional: only if you want direct access)
gcloud compute firewall-rules create allow-postgres \
    --allow tcp:5432 \
    --target-tags=streamlit-port
```

7. First time only: Access the VM to create a fake extra 2 GB of RAM

```bash
gcloud compute ssh discount-tracker-vm
```

```bash
# Create a 2GB file for swap
sudo fallocate -l 2G /swapfile                              # Create a 2GB file
sudo chmod 600 /swapfile                                    # Set permissions to read/write only
sudo mkswap /swapfile                                       # Create a swap file
sudo swapon /swapfile                                       # Activate swap file

# Make it permanent so it survives reboots
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify it worked (you should see 'Swap: 2.0Gi')
free -h
```

> Note: This is a first-time setup step for low-memory environments.

8. Install Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Allow your user to run docker without 'sudo'
sudo usermod -aG docker $USER
# IMPORTANT: Log out and log back in for this to take effect!
exit
```

9. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

10. Clone git repo (using PAT for auth)

```bash
git clone [REPO_URL]
```

11. Create .env file

Copy .env-example to .env.

```bash
cp .env-example .env
```

Fill in the .env using nano:

```bash
nano .env
```

12. Start and build docker images

```bash
docker compose up --build
```

13. Run orchestrator (you may need to restart the streamlit container for cache to clear)

```bash
make run-orchestrator-test
```

---

## Shutdown and cleanup

1. Shut down containers

```bash
docker compose down
```

2. Stop the VM

```bash
gcloud compute instances stop [VM_NAME] --zone=[ZONE]
```

e.g

```bash
gcloud compute instances stop discount-tracker-vm --zone=us-east1-c
```

This prevents the VM from consuming RAM and CPU. You are only billed for disk space used to store code.
This does NOT DELETE the VM. It just stops it.

3. Check (STATUS should = TERMINATED)

```bash
gcloud compute instances list
```

---

## Resuming work

1. Start the VM

```bash
gcloud compute instances start discount-tracker-vm --zone=us-east1-c
```

2. Access VM

```bash
gcloud compute ssh discount-tracker-vm
```

3. Start the Docker containers

```bash
cd ~/discount-tracker
docker compose up -d
```

4. Check containers are running:

```bash
docker ps
```

---

## Misc

Set up account for auth

```bash
gcloud config set account [ACCOUNT_EMAIL]
```

## Setting up cron schedule

```bash
# Enter crontab edit mode
crontab -e
```

Add these lines at the end:

```
# Existing text

0 0 * * * /usr/bin/docker exec discount_orchestrator python /app/orchestrate.py --itemcount 10 >> /home/santiago_villaverde07/logs/cron/sync_$(date +\%Y-\%m-\%d).log 2>&1
```

This sets up a cron schedule to run at midnight (UTC) and dump logs to a file.

Create the logs folder to prevent errors:
```bash
mkdir -p /home/santiago_villaverde07/logs/cron
```