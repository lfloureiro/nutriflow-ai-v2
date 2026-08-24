from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def validate_timezone_name(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("timezone must be a valid IANA timezone name.") from exc
    return value
