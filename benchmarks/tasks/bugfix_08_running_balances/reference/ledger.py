"""Replay account transactions to get running balances (amounts are integer cents)."""


def apply_transactions(transactions, opening=None):
    """Replay (account, cents) pairs in order, starting from the opening balances.

    Returns (history, balances): history lists an (account, balance after that
    transaction) pair for every transaction, and balances maps each account to its
    final balance.
    """
    balances = dict(opening) if opening is not None else {}
    history = []
    for account, cents in transactions:
        balances[account] = balances.get(account, 0) + cents
        history.append((account, balances[account]))
    return history, balances
