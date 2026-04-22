class RawPayloadWrapperPipeline:
    """Wraps each item as {"raw_payload": <item>} so GCS JSONL files have a
    consistent single-column schema that maps to the BigQuery external table."""

    def process_item(self, item, spider):
        return {"raw_payload": dict(item)}
