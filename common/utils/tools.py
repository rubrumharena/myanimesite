def safe_int(value: str) -> int | None:
    try:
        result = int(value) if value not in (None, '', 'null') else None
    except TypeError:
        result = None
    return result
