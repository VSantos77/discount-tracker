from run_spiders import execute_crawls
from utils.functions import get_db_connection
from utils.scripts.get_project_root_path import get_project_root_path
from dotenv import load_dotenv
import subprocess
import sys
import time
import os
import argparse

load_dotenv()

DB_SETTINGS = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("POSTGRES_DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

DBT_PROJECT_DIR = "discount_tracker_dbt"

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
    parser.add_argument("--spiders", type=str, default='', help="Comma-separated list of spiders to run (default: all)")
    parser.add_argument("--dry-run",type=str, default='0', help="Run spiders in dry-run mode (no items scraped)")
    args = parser.parse_args()

    print("🎼 Starting Orchestration Pipeline...")
    
    # 1. Run Scrapy Spiders (using your existing runner)
    try:
        crawl_results = execute_crawls(**vars(args))

        with open(get_project_root_path() / "utils" / "queries" / "insert_to_scrapy_run_stats.sql", 'r') as f:
            insert_query = f.read()

        # Store results in DB
        with get_db_connection(DB_SETTINGS) as conn:
            with conn.cursor() as cur:
                for spider_name, stats in crawl_results.items():
                    cur.execute(
                        insert_query,
                        (
                            spider_name,
                            stats['start_time'],
                            stats['finish_time'],
                            stats['count'],
                            stats['reason'],
                            stats['runtime']
                        )
                    )
                conn.commit()

        print('✅ Crawl results successfully loaded to DB')
    except Exception as e:
        print(f"❌ --- Error during spider execution or DB insertion: {e} ---")
        sys.exit(1)

    # 2. Run dbt Build (runs models, tests, snapshots, seeds)
    # We target 'dev_docker' which uses the env vars from docker-compose

    # First run dbt deps

    dbt_args = ["uv", "run", "--group", "orchestrator", "dbt", "deps", "--project-dir", DBT_PROJECT_DIR, "--profiles-dir", DBT_PROJECT_DIR, "--target", "dev_docker"]
    run_step(dbt_args, "dbt Deps")

    # Then run dbt build
    dbt_args = ["uv", "run", "--group", "orchestrator", "dbt", "build", "--project-dir", DBT_PROJECT_DIR, "--profiles-dir", DBT_PROJECT_DIR, "--target", "dev_docker"]
    run_step(dbt_args, "dbt Build")

if __name__ == "__main__":
    main()