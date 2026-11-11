"""Reports built on top of ledger.apply_transactions."""
from ledger import apply_transactions


def final_balances(transactions, opening=None):
    """Final balance of every account named in opening or in transactions."""
    _, balances = apply_transactions(transactions, opening)
    return balances


def overdrawn(transactions, opening=None):
    """Sorted names of the accounts whose final balance is below zero."""
    balances = final_balances(transactions, opening)
    return sorted(name for name, cents in balances.items() if cents < 0)


def daily_closing(days, opening=None):
    """Closing balances after each day; days is a list of transaction lists.

    Day 2 starts from the closing balances of day 1, and so on.
    """
    closings = []
    balances = opening
    for day in days:
        _, balances = apply_transactions(day, balances)
        closings.append(balances)
    return closings
