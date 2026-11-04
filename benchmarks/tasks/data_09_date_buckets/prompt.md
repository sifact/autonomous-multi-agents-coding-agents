Write `solution.py` with a function `bucket_events(path: str, bucket: str) -> dict[str, int]`.

`path` is a CSV file with the header `timestamp,user`. The sample file `events.csv` is in the
working directory. Count events per time bucket.

Timestamps are ISO 8601 date-times such as `2024-03-04T13:45:10`, `2024-03-04T13:45:10Z` or
`2024-03-04T13:45:10+02:00`. Convert every timestamp to UTC before bucketing. A timestamp
without an offset is already UTC. Rows whose timestamp cannot be parsed are skipped.

`bucket` is one of the following; any other value raises `ValueError`:

| bucket    | key format         | bucket covers                          |
|-----------|--------------------|----------------------------------------|
| `"hour"`  | `"2024-03-04 13:00"` | the UTC clock hour                   |
| `"day"`   | `"2024-03-04"`       | the UTC calendar day                 |
| `"week"`  | `"2024-03-04"`       | the ISO week, keyed by its **Monday** date |
| `"month"` | `"2024-03"`          | the UTC calendar month               |

The result contains every bucket from the earliest to the latest bucket that has an event,
**including buckets with no events, which get 0**, in ascending time order. No usable rows
gives `{}`. Read the file from the `path` argument, not from a hard-coded name. Use only the
standard library.
