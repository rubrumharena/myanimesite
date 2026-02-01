def safe_int(value: str) -> int | None:
    return int(value) if value not in (None, '', 'null') else None
