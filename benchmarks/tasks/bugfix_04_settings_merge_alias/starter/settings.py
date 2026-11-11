"""Application settings: built-in defaults plus per-user overrides."""

DEFAULTS = {
    "theme": "light",
    "editor": {"font_size": 12, "tabs": 4, "wrap": False},
    "paths": {"cache": "/tmp/cache", "logs": ["/var/log/app"]},
}


def merge(base: dict, overrides: dict) -> dict:
    """Combine two settings dicts; nested dicts are merged key by key."""
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(merge(merged[key], value))
        else:
            merged[key] = value
    return merged


def build_settings(overrides: dict | None = None) -> dict:
    """Settings for one user: DEFAULTS with the overrides applied."""
    return merge(DEFAULTS, overrides or {})
