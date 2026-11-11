# verdict.py

Writes the plain-language "did the graph beat the baselines" verdict from the numbers only.

- `compare(results)` compares the latest full-graph result with the latest single_agent and single_shot results on final pass and budget-matched pass.
- A winner is named only when both sides have at least 20 runs and the gap is at least 5 percentage points and at least 2 tasks; otherwise the line says "no clear difference" and states why.
- Every line carries both sample sizes, so a tiny sample can never read as a win.
- A cost line gives the graph's token multiple over each baseline (mean tokens per task), or says the cost cannot be compared.
- If the graph wins on final pass but not at a matched retry budget, it says the gain may come from extra retries; it is not a significance test.
