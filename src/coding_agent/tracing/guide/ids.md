# ids.py

Generates trace and span ids that do not depend on Python's seeded `random`.

- `SecureIdGenerator` is passed to the Langfuse client as `id_generator`.
- It draws 128-bit trace ids and 64-bit span ids from the `secrets` module.
- The benchmark runner calls `random.seed(seed + repeat)` before every task for reproducibility.
- OpenTelemetry's default generator uses that global `random`, which gave every task the same trace id and merged all runs into one trace.
- A regression test seeds `random` twice with the same value and checks that two runs get different trace ids.
