# single_shot.py

Baseline 1: one model call with the coder prompt, never executing anything.

- Makes exactly one `model.invoke` using the shared coder system prompt and the same `task_prompt` as the other systems.
- Parses the reply with the agents' `split_files`, so the `### FILE:` format rules are identical to the graph's.
- Never touches the sandbox, so `first_try_pass` is `None` and the runner grades its single output with the hidden tests.
- `model_name` is required so cost comes from the pricing table (`None` when unpriced); first, final and budget files are all the one output.
- If the call raises, the exception carries zero partial usage and the elapsed wall time for the runner's crash record.
