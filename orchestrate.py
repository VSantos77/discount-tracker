import subprocess
import sys
import time
import os
import argparse

def run_step(command, step_name):
    print(f"\n🚀 --- Starting: {step_name} ---")
    start = time.time()
    try:
        # Use sys.executable to ensure we use the same python interpreter (from the venv)
        if command[0] == "python":
            command[0] = sys.executable
            
        # Run the command and wait for it to finish. Check=True raises error on non-zero exit.
        subprocess.run(
            command,
            check=True,
            text=True,
            env=os.environ.copy() # Pass current env vars (DB credentials, etc.)
        )
        duration = time.time() - start
        print(f"✅ --- Completed: {step_name} (took {duration:.2f}s) ---")
    except subprocess.CalledProcessError as e:
        print(f"❌ --- Failed: {step_name} (Exit Code: {e.returncode}) ---")
        sys.exit(e.returncode)

def main():
    parser = argparse.ArgumentParser(description="Orchestrate ETL Pipeline")
    parser.add_argument("--itemcount", type=int, default=0, help="Pass item count limit to spiders")
    args = parser.parse_args()

    print("🎼 Starting Orchestration Pipeline...")
    
    # 1. Run Scrapy Spiders (using your existing runner)
    spider_cmd = ["python", "run_spiders.py"]
    if args.itemcount > 0:
        spider_cmd.extend(["--itemcount", str(args.itemcount)])
    run_step(spider_cmd, "Scrapy Crawl")

    # 2. Run dbt Build (runs models, tests, snapshots, seeds)
    # We target 'dev_docker' which uses the env vars from docker-compose

    # First run dbt deps

    dbt_args = ["uv", "run", "--group", "orchestrator", "dbt", "deps", "--project-dir", "discount_tracker_dbt", "--profiles-dir", "discount_tracker_dbt", "--target", "dev_docker"]
    run_step(dbt_args, "dbt Deps")

    # Then run dbt build
    dbt_args = ["uv", "run", "--group", "orchestrator", "dbt", "build", "--project-dir", "discount_tracker_dbt", "--profiles-dir", "discount_tracker_dbt", "--target", "dev_docker"]
    run_step(dbt_args, "dbt Build")

if __name__ == "__main__":
    main()