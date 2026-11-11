`ledger.py` and `summary.py` replay bank transactions (amounts are integer cents), and they
fail as soon as a transaction names an account that is not in the opening balances.

Example: `apply_transactions([("a", 500), ("b", -200), ("a", -100)])` should return
`([("a", 500), ("b", -200), ("a", 400)], {"a": 400, "b": -200})` but raises `KeyError: 'a'`.

Once that works, `daily_closing` must also give correct per-day results, and the caller's
data must be left alone. Contract (keep every name and signature):

- An account that is in neither the opening balances nor an earlier transaction starts at 0.
  Accounts that only appear in `opening` stay in the returned balances unchanged.
- `apply_transactions(transactions, opening=None)` never modifies `opening` and returns a
  balances dict that is a new dict, even when there are no transactions. Without `opening`
  every call starts from empty balances. The history holds the running balance of the
  transaction's account, in transaction order.
- `final_balances`, `overdrawn` and `daily_closing` (see their docstrings) keep their
  signatures. `daily_closing` returns one balances dict per day, each independent of the
  others: the dict for day 1 still shows day 1's balances after day 2 has been replayed. Its
  `opening` is not modified either.
