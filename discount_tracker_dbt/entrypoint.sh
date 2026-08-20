#!/bin/sh
set -e
exec dbt "$@" --vars "$(cat /app/schemas/spider_required_keys.yaml)"