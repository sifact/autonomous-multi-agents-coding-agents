`ledger.py` has a bug: `is_balanced` says a list of entries is out of balance even though the
amounts cancel out exactly on paper.

Example: `is_balanced([0.1, 0.2, -0.3])` should be `True` (10 + 20 - 30 cents is zero) but is
`False`, even though `balance([0.1, 0.2, -0.3])` correctly gives `0.0`.

Contract (keep every name and signature):

- Entries are dollar amounts with at most two decimals (credits positive, debits negative).
- `is_balanced(entries)` is `True` exactly when the total is zero to the cent, however many
  entries there are, and `False` otherwise: a total that is off by even one cent (0.01) is not
  balanced. An empty list is balanced. It returns a `bool`.
- `balance` and `largest_imbalance` already work and must keep working.
