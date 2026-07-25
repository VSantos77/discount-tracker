#!/usr/bin/env python3
"""
Integration test suite for the discount-tracker Cloud Workflow.

Requires Application Default Credentials:
    gcloud auth application-default login

Usage:
    python scripts/test_workflow.py                      # run all cases
    python scripts/test_workflow.py minimal_end_to_end   # run one case by name
    python scripts/test_workflow.py --list               # print available cases
"""

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from google.cloud.workflows.executions_v1 import ExecutionsClient
from google.cloud.workflows.executions_v1.types import Execution

PROJECT_ID = "vocal-tracer-484119-t7"
REGION = "us-east1"
WORKFLOW_NAME = "discount-tracker-prod-workflow"
WORKFLOW_PATH = f"projects/{PROJECT_ID}/locations/{REGION}/workflows/{WORKFLOW_NAME}"

POLL_INTERVAL = 15
DEFAULT_TIMEOUT = 900  # 15 min


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

def new_gcs_files_gt_zero(result: dict) -> bool:
    return result.get("new_gcs_files", 0) > 0


def dbt_execution_is_set(result: dict) -> bool:
    v = result.get("dbt_execution")
    return v is not None and v != ""


def all_spiders_scraped(result: dict) -> bool:
    spider_results = result.get("spider_results", {})
    return all(
        spider_results.get(s, {}).get("items_scraped", 0) > 0
        for s in ["galicia", "bbva", "naranjax"]
    )


# ---------------------------------------------------------------------------
# Test case definition
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    name: str
    description: str
    args: dict
    expect_failure: bool = False
    assertions: list[tuple[str, Callable[[dict], bool]]] = field(default_factory=list)
    timeout: int = DEFAULT_TIMEOUT


TEST_CASES: list[TestCase] = [
    TestCase(
        name="minimal_end_to_end",
        description="Single spider (galicia), 5-item cap — full pipeline: scrape → GCS gate → dbt",
        args={
            "spiders": ["galicia"],
            "close_spider_itemcount": 5,
            "dbt_cmd": "build --select stg_galicia+",
            "dbt_target": "local-dev",
        },
        assertions=[
            ("new_gcs_files > 0", new_gcs_files_gt_zero),
            ("dbt_execution is set", dbt_execution_is_set),
        ],
    ),
    TestCase(
        name="skip_dbt",
        description="Scrape galicia only, skip dbt — verifies skip_dbt branch and GCS gate",
        args={
            "spiders": ["galicia"],
            "close_spider_itemcount": 5,
            "skip_dbt": True,
        },
        assertions=[
            ("new_gcs_files > 0", new_gcs_files_gt_zero),
        ],
    ),
    TestCase(
        name="skip_scrapy",
        description="Skip scraping, run dbt on existing data — verifies skip_scrapy branch",
        args={
            "skip_scrapy": True,
            "dbt_cmd": "build --select stg_galicia+",
            "dbt_target": "local-dev",
        },
        assertions=[
            ("dbt_execution is set", dbt_execution_is_set),
        ],
    ),
    TestCase(
        name="all_spiders_parallel",
        description="All three spiders at 3-item cap, no dbt — verifies parallel execution and galicia inclusion",
        args={
            "close_spider_itemcount": 3,
            "skip_dbt": True,
        },
        assertions=[
            ("all spiders scraped > 0 items", all_spiders_scraped),
        ],
    ),
    TestCase(
        name="invalid_spider_fails",
        description="Invalid spider name — verifies the workflow raises an error rather than silently succeeding",
        args={
            "spiders": ["nonexistent"],
            "skip_dbt": True,
        },
        expect_failure=True,
        timeout=300,
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def poll(client: ExecutionsClient, name: str, timeout: int) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        execution = client.get_execution(name=name)
        state = execution.state

        if state == Execution.State.SUCCEEDED:
            result = json.loads(execution.result) if execution.result else {}
            return {"status": "SUCCEEDED", "result": result}

        if state in (Execution.State.FAILED, Execution.State.CANCELLED):
            error = execution.error.payload if execution.error else "unknown"
            return {"status": state.name, "error": error}

        print(f"    {state.name} — waiting {POLL_INTERVAL}s")
        time.sleep(POLL_INTERVAL)

    client.cancel_execution(name=name)
    return {"status": "TIMEOUT"}


def run_case(client: ExecutionsClient, case: TestCase) -> bool:
    print(f"\n{'─' * 64}")
    print(f"  TEST:  {case.name}")
    print(f"  DESC:  {case.description}")
    print(f"  ARGS:  {json.dumps(case.args)}")
    print(f"  START: {datetime.now().strftime('%H:%M:%S')}")

    execution = client.create_execution(
        parent=WORKFLOW_PATH,
        execution=Execution(argument=json.dumps(case.args)),
    )
    print(f"  EXEC:  {execution.name.split('/')[-1]}")

    t0 = time.time()
    outcome = poll(client, execution.name, case.timeout)
    elapsed = time.time() - t0

    status = outcome["status"]
    print(f"  STATUS: {status} ({elapsed:.0f}s)")

    if case.expect_failure:
        ok = status == "FAILED"
        marker = "PASS" if ok else "FAIL"
        detail = outcome.get("error", "")[:120] if ok else f"expected FAILED, got {status}"
        print(f"  [{marker}] failed as expected: {detail}" if ok else f"  [{marker}] {detail}")
        return ok

    if status != "SUCCEEDED":
        print(f"  [FAIL] {outcome.get('error', status)}")
        return False

    result = outcome["result"]
    passed = True
    for label, check in case.assertions:
        ok = check(result)
        print(f"  {'[PASS]' if ok else '[FAIL]'} {label}")
        if not ok:
            passed = False

    if not case.assertions:
        print("  [PASS] succeeded")

    return passed


def main() -> None:
    argv = sys.argv[1:]

    if "--list" in argv:
        for case in TEST_CASES:
            print(f"  {case.name:<28}  {case.description}")
        return

    target = argv[0] if argv else None
    cases = [c for c in TEST_CASES if target is None or c.name == target]

    if not cases:
        available = [c.name for c in TEST_CASES]
        print(f"No test case '{target}'. Available: {available}")
        sys.exit(1)

    client = ExecutionsClient()
    results = [run_case(client, c) for c in cases]

    passed = sum(results)
    total = len(results)
    print(f"\n{'═' * 64}")
    print(f"  {passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
