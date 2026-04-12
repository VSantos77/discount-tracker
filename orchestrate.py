from run_spiders import execute_crawls
from utils.functions import get_db_connection
from utils.functions import get_project_root_path
from utils.configs import DB_SETTINGS
from utils.configs import DBT_PROJECT_DIR
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


def step_spiders(args):
    """Run Scrapy spiders and persist crawl stats to DB."""
    try:
        crawl_results = execute_crawls(
            itemcount=args.itemcount,
            spiders=args.spiders
        )

        with open(get_project_root_path() / "utils" / "queries" / "insert_to_scrapy_run_stats.sql", 'r') as f:
            insert_query = f.read()

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

        print('✅ Crawl stats successfully loaded to DB')
    except Exception as e:
        print(f"❌ --- Error during spider execution or DB insertion: {e} ---")
        sys.exit(1)


def step_load(args):
    """Batch-load JSON files produced by spiders into raw_discounts."""
    run_step(["python", "load_raw_json.py"], "Load raw JSON to Postgres")


def step_dbt(args):
    """Run dbt build (deps pre-installed in Docker image)."""
    run_step(
        ["uv", "run", "--group", "orchestrator", "dbt", "build",
         "--project-dir", DBT_PROJECT_DIR, "--profiles-dir", DBT_PROJECT_DIR,
         "--target", args.dbt_target],
        "dbt Build"
    )


def main():
    parser = argparse.ArgumentParser(description="Orchestrate ETL Pipeline")
    parser.add_argument(
        "--step",
        choices=["spiders", "load", "dbt"],
        default=None,
        help="Run a single pipeline step. Omit to run all steps in sequence."
    )
    parser.add_argument("--itemcount", type=int, default=0, help="Pass item count limit to spiders")
    parser.add_argument("--spiders", type=str, default='', help="Comma-separated list of spiders to run (default: all)")
    parser.add_argument("--dbt-target", type=str, default='dev_docker', help="dbt target to use (default: dev_docker)")

    args = parser.parse_args()

    if args.step == "spiders":
        print("🎼 Running step: Spiders")
        step_spiders(args)
    elif args.step == "load":
        print("🎼 Running step: Load")
        step_load(args)
    elif args.step == "dbt":
        print("🎼 Running step: dbt")
        step_dbt(args)
    else:
        print("🎼 Running full pipeline: Spiders → Load → dbt")
        step_spiders(args)
        step_load(args)
        step_dbt(args)

    print("\n🎉 Pipeline finished successfully.")

if __name__ == "__main__":
    main()