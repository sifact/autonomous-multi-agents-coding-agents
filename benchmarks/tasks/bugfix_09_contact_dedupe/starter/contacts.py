"""A tiny contact book: each contact is a dict with at least a 'name' key."""
from normalize import normalize_name


def dedupe(contacts: list[dict]) -> list[dict]:
    """Drop contacts whose name repeats an earlier one; keep the first of each."""
    seen = set()
    unique = []
    for contact in contacts:
        key = contact["name"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(contact)
    return unique


def find_contact(contacts: list[dict], name: str) -> dict | None:
    """The first contact whose name matches, or None."""
    wanted = normalize_name(name)
    for contact in contacts:
        if normalize_name(contact["name"]) == wanted:
            return contact
    return None
