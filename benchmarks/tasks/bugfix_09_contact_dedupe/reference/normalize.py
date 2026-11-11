"""Text normalisation shared by the contact tools."""


def normalize_name(name: str) -> str:
    """Canonical form of a person's name, used to compare two spellings."""
    return " ".join(name.casefold().split())


def normalize_email(email: str) -> str:
    """Canonical form of an email address: no surrounding spaces, lower case."""
    return email.strip().lower()


def initials(name: str) -> str:
    """Upper-case first letters of each word of the name, e.g. 'ada king' -> 'AK'."""
    return "".join(word[0] for word in normalize_name(name).split()).upper()
