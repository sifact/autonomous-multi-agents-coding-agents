import csv


def _is_valid(email: str) -> bool:
    if not email or any(ch.isspace() for ch in email) or email.count("@") != 1:
        return False
    local, domain = email.split("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def clean_emails(path: str) -> list[str]:
    seen: dict[str, None] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            email = row["email"].strip().lower()
            if _is_valid(email):
                seen.setdefault(email)
    return list(seen)
