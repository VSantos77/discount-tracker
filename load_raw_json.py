"""
Standalone batch loader: reads .jsonl files produced by Scrapy's FEEDS export
from data/landing/<spider_name>/<timestamp>.jsonl and inserts them as raw JSONB
rows into the raw_discounts table.

Directory layout expected:
    data/landing/
        bbva/
            2026-04-10T14-30-00+00-00.jsonl
        galicia/
            2026-04-10T14-30-05+00-00.jsonl

After a successful load the source file is moved to data/landing/<spider>/processed/
to prevent re-insertion on subsequent runs.

Usage:
    python load_raw_json.py [--landing-dir <path>]
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

from utils.configs import DB_SETTINGS
from utils.functions import get_project_root_path


# Filename pattern produced by Scrapy's %(time)s token: <YYYY-MM-DDTHH-MM-SS+TZ-OFF>.jsonl
# e.g. 2026-04-10T14-13-34+00-00.jsonl
_FILENAME_RE = re.compile(r'^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})(?P<tz>[+-]\d{2}-\d{2})?\.jsonl$')

_INSERT_SQL = """
    INSERT INTO raw.raw_discounts (spider_name, scraped_at, raw_payload)
    VALUES %s
"""


def parse_filename(filename: str):
    """Return scraped_at parsed from a .jsonl filename, or None if it doesn't match."""
    match = _FILENAME_RE.match(filename)
    if not match:
        return None
    ts_str = match.group('ts')   # e.g. 2026-04-10T14-13-34
    tz_str = match.group('tz')   # e.g. +00-00, or None
    scraped_at = datetime.datetime.strptime(ts_str, '%Y-%m-%dT%H-%M-%S')
    if tz_str:
        # Convert +00-00 / -03-00 -> +00:00 / -03:00 for fromisoformat
        sign = tz_str[0]
        parts = tz_str[1:].split('-')
        offset = datetime.timezone(datetime.timedelta(hours=int(sign + parts[0]), minutes=int(parts[1])))
        scraped_at = scraped_at.replace(tzinfo=offset)
    else:
        scraped_at = scraped_at.replace(tzinfo=datetime.timezone.utc)
    return scraped_at


def load_file(conn, file_path: Path, spider_name: str, scraped_at: datetime.datetime) -> int:
    """Insert all items from a .jsonl file into raw_discounts. Returns the number of rows inserted."""
    with open(file_path, 'r', encoding='utf-8') as f:
        items = [json.loads(line) for line in f if line.strip()]

    if not items:
        print(f"  [skip] {file_path.name} — empty file")
        return 0

    rows = [(spider_name, scraped_at, psycopg2.extras.Json(item)) for item in items]

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, _INSERT_SQL, rows)
    conn.commit()
    return len(rows)


def load_raw_json_data(landing_dir: str = None) -> None:
    """
    Load all .jsonl files found under landing_dir into raw_discounts.
    Callable directly from orchestrate.py or other Python code.
    Raises on failure instead of calling sys.exit so callers can handle errors.
    """
    if landing_dir is None:
        landing_dir = str(get_project_root_path() / 'data' / 'landing')

    landing_path = Path(landing_dir)

    if not landing_path.exists():
        raise FileNotFoundError(f"Landing directory not found: {landing_path}")

    # Collect all .jsonl files from per-spider subdirectories (skip processed/ inside each)
    jsonl_files: list[tuple[Path, str]] = []  # (file_path, spider_name)
    for spider_dir in sorted(landing_path.iterdir()):
        if not spider_dir.is_dir() or spider_dir.name == 'processed':
            continue
        spider_name = spider_dir.name
        for file_path in sorted(spider_dir.glob('*.jsonl')):
            jsonl_files.append((file_path, spider_name))

    if not jsonl_files:
        print(f"No .jsonl files found under {landing_path}")
        return

    print(f"Found {len(jsonl_files)} file(s) to process\n")

    total_inserted = 0
    total_files = 0

    with psycopg2.connect(**DB_SETTINGS) as conn:
        for file_path, spider_name in jsonl_files:
            scraped_at = parse_filename(file_path.name)
            if scraped_at is None:
                print(f"  [skip] {file_path} — filename does not match expected pattern")
                continue

            print(f"  Loading {file_path.relative_to(landing_path)} (spider={spider_name}, scraped_at={scraped_at.isoformat()})")

            try:
                n = load_file(conn, file_path, spider_name, scraped_at)
                print(f"  ✅ Inserted {n} rows")
                total_inserted += n
                total_files += 1

                # Archive the processed file into a processed/ subfolder next to the spider dir
                processed_dir = file_path.parent / 'processed'
                processed_dir.mkdir(exist_ok=True)
                shutil.move(str(file_path), processed_dir / file_path.name)
            except Exception as e:
                conn.rollback()
                print(f"  ❌ Failed to load {file_path.name}: {e}")
                raise

    print(f"\n✅ Done — {total_inserted} total rows inserted from {total_files} file(s)")


def main():
    parser = argparse.ArgumentParser(description="Batch-load Scrapy .jsonl feed files into raw_discounts")
    parser.add_argument(
        '--landing-dir',
        type=str,
        default=None,
        help='Root landing directory containing per-spider subdirectories (default: data/landing/)',
    )
    args = parser.parse_args()

    try:
        load_raw_json_data(landing_dir=args.landing_dir)
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
