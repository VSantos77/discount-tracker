import json
import subprocess
from pathlib import Path

import pytest
import yaml

SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "spider_required_keys.yaml"

def load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return yaml.safe_load(f)


def get_spider_names() -> list[str]:
    return list(load_schema().keys())


def load_required_keys(spider_name: str) -> list[str]:
    return load_schema()[spider_name]


def has_nested_key(data: dict, path: str):
    """Checks if keys (including nested) exist in dict. Return True if key exists, False otherwise."""
    current = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return True


@pytest.mark.parametrize("spider_name", get_spider_names())
def test_spider_produces_valid_items(spider_name, tmp_path):
    """Test scrapy spider by running a fast crawl and testing the output
    for items and extracted payload keys"""
    output_file = tmp_path / f"{spider_name}.jsonl"
    required_keys = load_required_keys(spider_name)

    result = subprocess.run(
        [
            "scrapy", "crawl", spider_name,
            "-s", "CLOSESPIDER_ITEMCOUNT=1",
            "-s", "CONCURRENT_REQUESTS=1", # Reduce spent time processing excess requests
            "-o", str(output_file),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"{spider_name}: crawl failed (exit code {result.returncode})\n"
        f"stderr:\n{result.stderr}"
    )

    assert output_file.exists(), f"{spider_name}: no output file was generated."

    lines = output_file.read_text(encoding='utf-8').splitlines()
    assert len(lines) >= 1, f"{spider_name}: no items were scraped."

    item = json.loads(lines[0])["raw_payload"]

    missing = [k for k in required_keys if not has_nested_key(item, k)]
    assert not missing, f"{spider_name}: keys missing: {missing}"