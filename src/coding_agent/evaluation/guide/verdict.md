# verdict.py

Writes the plain-language "did the graph beat the baselines" verdict from the numbers only, paired by task.

- `compare(results)` pairs the latest full-graph result with the latest single_agent and single_shot results on the task ids both ran, scoring each task as the mean over its repeats; it never compares percentages across different task sets.
- Tasks where either side had a crashed run are left out and reported; if more than 10% of the shared tasks would be left out, or a system crashed on every run, the pair is "not comparable" (infrastructure failures, not agent quality), never "worse".
- At least 20 shared, non-crashed tasks (`MIN_SHARED_TASKS`) are needed, so the 10-task fast subset is labelled a smoke test only; fewer tasks, or different task sets, read "no clear difference".
- "Better" or "worse" needs a mean paired difference of at least 5 points AND an exact two-sided sign test (`sign_test_p`, `math.comb`) with p < 0.05 on the non-tied tasks, in the same direction.
- Each sentence for final pass and budget-matched pass carries shared tasks, runs per system, wins/losses/ties, the difference and the token multiple, and says "the gain disappears when the retry budget is matched" when the two disagree.
