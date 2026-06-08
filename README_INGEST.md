Ingestion and chunking

Run a quick self-test that creates sample chunks:

```bash
python3 src/ingest.py --test
```

To ingest local `documents/` and produce `data/chunks.jsonl`:

```bash
python3 src/ingest.py --out data/chunks.jsonl
```

Note: remote fetching for URLs listed in `data/sources.json` is left as a separate step to avoid introducing network dependencies in tests.
