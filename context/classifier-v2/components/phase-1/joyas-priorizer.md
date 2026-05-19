# joyas-priorizer

**Type:** EMR Serverless (PySpark)
**Trigger:** Started by `emr-job-trigger` Lambda
**Purpose:** Loads enterprise keywords as a Spark broadcast variable, scans a decompressed tree NDJSON file, matches keywords against file names, and outputs a reduced tree containing only the matched documents (crown jewels).

---

## Input

### Arguments (from emr-job-trigger Lambda)

```
spark-submit job.py <decompressed_bucket> <tree_key>
```

| Arg | Example | Description |
|---|---|---|
| `decompressed_bucket` | `kriptos-poc-harias-decompressed-trees` | S3 bucket with decompressed trees |
| `tree_key` | `ent-001/station-001/0ce84cb1.jsonl` | S3 key of the specific tree to process |

### Data Sources

1. **Tree file:** `s3a://{decompressed_bucket}/{tree_key}` — NDJSON, one JSON per line
2. **Keywords file:** `s3a://{keywords_bucket}/{enterprise_id}.json` — JSON with `keywords` array

The `enterprise_id` is extracted from the `tree_key` (first path segment).

## Output

**S3 path:** `s3a://{crown_jewels_bucket}/{enterprise_id}/{station_id}/`

Spark writes NDJSON output (one or more part files). Each matched document includes the original 5 fields + `matched_keywords`:

```jsonl
{"name":"Q1-Financial-Report","path":"/Users/jdoe/Documents/Finance/","size":245780,"extension":"pdf","modified_date":"2026-04-14T09:15:22Z","matched_keywords":["financial"]}
```

| Field | Type | Description |
|---|---|---|
| `name` | string | Original from tree |
| `path` | string | Original from tree |
| `size` | number | Original from tree |
| `extension` | string | Original from tree |
| `modified_date` | string | Original from tree |
| `matched_keywords` | string[] | **New** — list of keywords that matched this file's name |

## Processing Logic

```
1. Parse enterprise_id and station_id from tree_key
2. Load keywords/{enterprise_id}.json from S3
3. Parse keywords array (supports both flat array and {"keywords": [...]} format)
4. Lowercase + strip all keywords
5. Create Spark broadcast variable with the keyword list
6. Read tree NDJSON into DataFrame
7. Define UDFs:
   a. has_match(name) → boolean: does name contain any keyword?
   b. get_matches(name) → string[]: which keywords matched?
8. Filter DataFrame: keep only rows where has_match(name) == true
9. Add matched_keywords column
10. Coalesce to 1 partition (single output file)
11. Write as JSON to crown_jewels/{enterprise_id}/{station_id}/
12. mode("overwrite") — replaces previous output for same station
```

## Validations

### Input Validation

1. **Argument count:** exactly 2 arguments (bucket, key). Exit with code 1 if wrong.
2. **Key format:** must match `{enterprise_id}/{station_id}/{tree_id}.jsonl`. Exit with code 1 if unparseable.
3. **Keywords file exists:** if `keywords/{enterprise_id}.json` is missing or empty, log WARNING and exit gracefully (no crash, no output).
4. **Keywords format:** accept both `["kw1", "kw2"]` and `{"keywords": ["kw1", "kw2"]}`. Log ERROR if neither format matches.

### Data Quality Validation (SHOULD implement)

5. **Empty tree:** if the tree NDJSON has 0 rows, log INFO and exit (no output).
6. **Name field exists:** if the DataFrame has no `name` column, try `nombre` (Spanish). If neither exists, log ERROR and exit.
7. **Keyword count sanity check:** if keywords > 10K, log WARN (unexpected, may impact performance).
8. **Output validation:** log the match count and match rate (`matched / total`). If match rate is > 80%, log WARN (keywords may be too broad).

## Error Handling

| Scenario | Action | Log Level | EMR Exit Code |
|---|---|---|---|
| Wrong argument count | Log and exit | ERROR | 1 |
| Unparseable S3 key | Log and exit | ERROR | 1 |
| Keywords file not found | Log and exit gracefully | WARN | 0 |
| Keywords file corrupt JSON | Log and exit | ERROR | 1 |
| Tree file not found | Log and exit | ERROR | 1 |
| Tree file corrupt NDJSON | Spark skips corrupt records (mode="PERMISSIVE") | WARN | 0 |
| S3 write permission denied | Crash with stack trace | ERROR | 1 |
| OOM (tree too large for memory) | Crash | ERROR | 1 — increase executor memory |

### No Auto-Retry

EMR Serverless jobs are NOT automatically retried. If a job fails:
- The `emr-job-trigger-dlq` catches the original event for manual reprocessing.
- CloudWatch alarm fires on EMR job FAILED state.
- Manual investigation required (check Spark UI via `get-dashboard-for-job-run`).

## Logging

Spark logs go to EMR's internal logging. To access:

```bash
aws emr-serverless get-dashboard-for-job-run \
  --application-id <app_id> \
  --job-run-id <job_run_id>
```

### Application-level logs (via Python logger)

| Event | Level | Fields |
|---|---|---|
| Job started | INFO | enterprise_id, station_id, tree_key |
| Keywords loaded | INFO | enterprise_id, keyword_count |
| No keywords found | WARN | enterprise_id |
| Tree loaded | INFO | row_count |
| Matches found | INFO | match_count, total_count, match_rate |
| Output written | INFO | output_path |
| No matches | INFO | enterprise_id, station_id — "0 matches, no output written" |

### TODO (production)

Configure EMR Serverless logging destination to a dedicated S3 bucket:

```python
"configurationOverrides": {
    "monitoringConfiguration": {
        "s3MonitoringConfiguration": {
            "logUri": "s3://kriptos-{env}-emr-logs/"
        }
    }
}
```

## Configuration

| Source | Variable | Value |
|---|---|---|
| Spark env | `KEYWORDS_BUCKET` | `kriptos-{env}-keywords` |
| Spark env | `CROWN_JEWELS_BUCKET` | `kriptos-{env}-crown-jewels` |
| Spark config | `spark.dynamicAllocation.enabled` | `false` |
| Spark config | `spark.executor.instances` | `1` |
| Spark config | `spark.executor.memory` | `1g` |
| Spark config | `spark.executor.cores` | `1` |
| Spark config | `spark.driver.memory` | `1g` |
| Spark config | `spark.driver.cores` | `1` |

### Scaling for Production

| Scale | Config Change |
|---|---|
| Trees up to 100K docs | Current config (1 executor, 1g) |
| Trees 100K–1M docs | `spark.executor.memory=2g` |
| Trees 1M–10M docs | `spark.executor.instances=2`, `spark.executor.memory=4g` |
| Trees > 10M docs | Enable dynamic allocation, increase max capacity |

## Performance

| Scale | Expected Duration | Memory |
|---|---|---|
| 12 docs, 10 keywords (POC) | ~30 sec (mostly Spark overhead) | 1g |
| 6K docs, 5K keywords (typical station) | ~30–60 sec | 1g |
| 100K docs, 5K keywords | ~1–2 min | 1g |
| 1M docs, 5K keywords | ~2–5 min | 2g |
| 10M docs, 5K keywords | ~5–15 min | 4g |

**Note:** for small files (< 10K docs), the Spark overhead dominates. The actual matching takes milliseconds. EMR Serverless cold start adds 2–3 minutes on top.

## Matching Semantics (current implementation)

**Algorithm:** Naive substring matching (`keyword in name.lower()`).

**Behavior:**

| Input Name | Keyword | Match? | Why |
|---|---|---|---|
| `Q1-Financial-Report` | `financial` | YES | `"financial" in "q1-financial-report"` |
| `Board-Minutes-March` | `board minutes` | NO | `"board minutes" not in "board-minutes-march"` (space vs hyphen) |
| `CONFIDENTIAL-doc` | `confidential` | YES | Case-insensitive (lowered) |

### Open: Matching Improvements (not implemented)

| Improvement | Description | Impact |
|---|---|---|
| Normalize hyphens/underscores to spaces | `"board-minutes"` → `"board minutes"` before matching | Catches hyphenated names |
| Aho-Corasick algorithm | Build automaton from keywords, O(n) scan | 50–100x faster for large keyword sets |
| Word boundary matching | Match `"contract"` only at word boundaries | Prevents false positives like `"subcontractor"` |
| Stemming | `"contracts"` matches `"contract"` | More recall, more false positives |
| Extension pre-filter | Only match against `.pdf`, `.docx`, `.xlsx` | Reduces noise from images, system files |

The matching strategy is a **team decision** flagged as an open question. See [overview.md](overview.md#open-questions-from-poc).

## Security Considerations

1. **Cross-enterprise isolation:** the job reads keywords for ONE enterprise (derived from the tree's key). It cannot access another enterprise's keywords (scoped by S3 path).
2. **Output overwrite:** `mode("overwrite")` means each run replaces the previous output. If an attacker triggers a job with a crafted S3 key, they could overwrite crown jewel output. Mitigated by: only `emr-job-trigger` Lambda can start jobs, and it parses the key from a real S3 event.
3. **No PII in output:** the crown jewels output contains file metadata only (name, path, size, extension, date). No file content is read or exposed.
4. **EMR execution role is scoped:** read from decompressed_trees + keywords, write to crown_jewels only.

## Dependencies

| Service | Operation | Why |
|---|---|---|
| S3 (decompressed_trees) | Read | Source tree NDJSON |
| S3 (keywords) | Read | Enterprise keywords + job script |
| S3 (crown_jewels) | Read + Write + Delete + List | Output (overwrite requires all 4) |
| CloudWatch Logs | Write | Spark driver/executor logs |

## Edge Cases

| Case | Behavior |
|---|---|
| Keywords file missing | Log WARN, exit with code 0, no output |
| Keywords file empty (`{"keywords": []}`) | 0 matches, no output |
| All documents match | Full tree copied to crown_jewels (rare — means keywords are too broad) |
| No documents match | No output written to crown_jewels |
| Tree file has non-standard field names | Tries `name`, falls back to `nombre` |
| Very large keyword file (> 10K keywords) | Works but slower. Log WARN. Consider Aho-Corasick. |
| Duplicate tree_id (re-upload) | Output overwritten — latest wins |
| Concurrent jobs for same enterprise/station | Last writer wins (S3 eventual consistency). Unlikely with EventBridge dedup. |
