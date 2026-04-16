import argparse
import subprocess
import yaml

from prefect import flow, task

from load_raw_json import load_raw_json_data
from run_spiders import execute_crawls
from utils.functions import get_project_root_path


def get_active_spiders() -> list[str]:
    path = get_project_root_path() / "utils" / "spider_config.yaml"
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return [s["name"] for s in config["spiders"] if s["active"]]


@task(name="run-spiders", log_prints=True)
def task_run_spiders(spiders: str = "", itemcount: int = 0) -> dict:
    active_spiders = get_active_spiders()

    if not spiders:
        spiders = ",".join(active_spiders)
    else:
        requested = [s.strip() for s in spiders.split(",")]
        invalid = [s for s in requested if s not in active_spiders]
        if invalid:
            raise ValueError(
                f"Invalid spider names: {', '.join(invalid)}. Active: {', '.join(active_spiders)}"
            )
        spiders = ",".join(requested)

    crawl_results = execute_crawls(itemcount=itemcount, spiders=spiders)
    return crawl_results


@task(name="load-raw-json", log_prints=True)
def task_load_raw_json(landing_dir: str = None) -> None:
    load_raw_json_data(landing_dir=landing_dir)


@task(name="run-dbt", log_prints=True)
def task_run_dbt(dbt_target: str = "prod") -> None:
    print(f"🚀 Running dbt build with target: {dbt_target}")
    subprocess.run(
        [
            "uv", "run", "--group", "orchestrator",
            "dbt", "build",
            "--target", dbt_target,
        ],
        check=True,
        text=True,
    )


@flow(name="discount-tracker-pipeline", log_prints=True)
def discount_tracker_pipeline(
    spiders: str = "",
    itemcount: int = 0,
    dbt_target: str = "prod",
) -> None:
    task_run_spiders(spiders=spiders, itemcount=itemcount)
    task_load_raw_json()
    task_run_dbt(dbt_target=dbt_target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrate ETL Pipeline")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run in serve mode: register the deployment and poll for runs (long-running)",
    )
    parser.add_argument("--spiders", type=str, default="", help="Comma-separated list of spiders (default: all active)")
    parser.add_argument("--itemcount", type=int, default=0, help="Item count limit for spiders (0 = unlimited)")
    parser.add_argument("--dbt-target", type=str, default="prod", help="dbt target (default: prod)")
    args = parser.parse_args()

    if args.serve:
        discount_tracker_pipeline.serve(name="discount-tracker-pipeline")
    else:
        discount_tracker_pipeline(
            spiders=args.spiders,
            itemcount=args.itemcount,
            dbt_target=args.dbt_target,
        )
